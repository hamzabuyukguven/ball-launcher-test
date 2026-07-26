#!/usr/bin/env python3

import json
import math
import re
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple

import rclpy
from naval_interfaces.msg import (
    FireCommand,
    GunInfo,
    GunRateCommand,
    GunStatusInfo,
    PlatformPositionInfo,
    PlatformVelocityInfo,
    StabilizationData,
    TargetPositionInfo,
)
from rclpy.node import Node
from std_msgs.msg import String


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def wrap_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def vector_add(
    first: Tuple[float, float, float],
    second: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    return tuple(
        first[index] + second[index]
        for index in range(3)
    )


def vector_subtract(
    first: Tuple[float, float, float],
    second: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    return tuple(
        first[index] - second[index]
        for index in range(3)
    )


def vector_scale(
    vector: Tuple[float, float, float],
    scalar: float,
) -> Tuple[float, float, float]:
    return tuple(value * scalar for value in vector)


def vector_length(
    vector: Tuple[float, float, float],
) -> float:
    return math.sqrt(sum(value * value for value in vector))


def matrix_multiply(first, second):
    return tuple(
        tuple(
            sum(
                first[row][index] * second[index][column]
                for index in range(3)
            )
            for column in range(3)
        )
        for row in range(3)
    )


def matrix_vector_multiply(matrix, vector):
    return tuple(
        sum(
            matrix[row][column] * vector[column]
            for column in range(3)
        )
        for row in range(3)
    )


def matrix_transpose(matrix):
    return tuple(
        tuple(matrix[column][row] for column in range(3))
        for row in range(3)
    )


def rotation_x(angle: float):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return (
        (1.0, 0.0, 0.0),
        (0.0, cosine, -sine),
        (0.0, sine, cosine),
    )


def rotation_y(angle: float):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return (
        (cosine, 0.0, sine),
        (0.0, 1.0, 0.0),
        (-sine, 0.0, cosine),
    )


def rotation_z(angle: float):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return (
        (cosine, -sine, 0.0),
        (sine, cosine, 0.0),
        (0.0, 0.0, 1.0),
    )


def rotation_from_rpy(
    roll: float,
    pitch: float,
    yaw: float,
):
    return matrix_multiply(
        rotation_z(yaw),
        matrix_multiply(
            rotation_y(pitch),
            rotation_x(roll),
        ),
    )


class AutoEngagementTestController(Node):
    """Phone-only automatic aiming test layer.

    This node does not modify or replace the gRPC backend path. It remains
    IDLE until a START command arrives on /test/auto_engage_command.
    """

    TERMINAL_STATES = {
        "IDLE",
        "COMPLETE",
        "CANCELLED",
        "ABORTED",
        "ERROR",
    }

    def __init__(self) -> None:
        super().__init__("auto_engagement_test_controller")

        self.declare_parameter("control_rate_hz", 20.0)
        self.declare_parameter("default_muzzle_velocity", 60.0)
        self.declare_parameter("gravity", 9.81)
        self.declare_parameter("fire_latency", 0.20)
        self.declare_parameter("target_aim_offset_z", 0.80)
        self.declare_parameter("muzzle_clearance", 0.30)
        self.declare_parameter(
            "projectile_inherits_platform_velocity",
            False,
        )
        self.declare_parameter("minimum_range", 2.0)
        self.declare_parameter("pan_kp", 1.6)
        self.declare_parameter("tilt_kp", 1.6)
        self.declare_parameter("max_pan_rate", 0.20)
        self.declare_parameter("max_tilt_rate", 0.12)
        self.declare_parameter("pan_tolerance_deg", 0.50)
        self.declare_parameter("tilt_tolerance_deg", 0.50)

        # Nişan yakalandıktan sonra küçük dalga kaynaklı konum
        # değişikliklerinin kontrolü tekrar açmasını engelleyen
        # bırakma toleransları.
        self.declare_parameter(
            "pan_release_tolerance_deg",
            0.75,
        )
        self.declare_parameter(
            "tilt_release_tolerance_deg",
            0.75,
        )

        self.declare_parameter("gun_rate_tolerance", 0.040)
        self.declare_parameter("platform_rate_tolerance", 0.060)
        self.declare_parameter("settle_time", 0.60)
        self.declare_parameter("overall_timeout", 45.0)
        self.declare_parameter("telemetry_timeout", 1.50)
        self.declare_parameter("velocity_filter_alpha", 0.12)

        # Target pose üzerindeki küçük dalga / fizik titreşimlerini
        # filtreler. Hareketli target takibi korunur.
        self.declare_parameter(
            "target_position_filter_alpha",
            0.20,
        )

        self.control_rate_hz = float(
            self.get_parameter("control_rate_hz").value
        )
        self.default_muzzle_velocity = float(
            self.get_parameter("default_muzzle_velocity").value
        )
        self.gravity = float(self.get_parameter("gravity").value)
        self.fire_latency = float(
            self.get_parameter("fire_latency").value
        )
        self.target_aim_offset_z = float(
            self.get_parameter("target_aim_offset_z").value
        )
        self.muzzle_clearance = float(
            self.get_parameter("muzzle_clearance").value
        )
        self.projectile_inherits_platform_velocity = bool(
            self.get_parameter(
                "projectile_inherits_platform_velocity"
            ).value
        )
        self.minimum_range = float(
            self.get_parameter("minimum_range").value
        )
        self.pan_kp = float(self.get_parameter("pan_kp").value)
        self.tilt_kp = float(self.get_parameter("tilt_kp").value)
        self.max_pan_rate = float(
            self.get_parameter("max_pan_rate").value
        )
        self.max_tilt_rate = float(
            self.get_parameter("max_tilt_rate").value
        )
        self.pan_tolerance = math.radians(
            float(self.get_parameter("pan_tolerance_deg").value)
        )
        self.tilt_tolerance = math.radians(
            float(self.get_parameter("tilt_tolerance_deg").value)
        )
        self.pan_release_tolerance = math.radians(
            float(
                self.get_parameter(
                    "pan_release_tolerance_deg"
                ).value
            )
        )
        self.tilt_release_tolerance = math.radians(
            float(
                self.get_parameter(
                    "tilt_release_tolerance_deg"
                ).value
            )
        )
        self.gun_rate_tolerance = float(
            self.get_parameter("gun_rate_tolerance").value
        )
        self.platform_rate_tolerance = float(
            self.get_parameter("platform_rate_tolerance").value
        )
        self.settle_time = float(
            self.get_parameter("settle_time").value
        )
        self.overall_timeout = float(
            self.get_parameter("overall_timeout").value
        )
        self.telemetry_timeout = float(
            self.get_parameter("telemetry_timeout").value
        )
        self.velocity_filter_alpha = float(
            self.get_parameter("velocity_filter_alpha").value
        )
        self.target_position_filter_alpha = float(
            self.get_parameter(
                "target_position_filter_alpha"
            ).value
        )

        self.geometry = self.load_active_gun_geometry()
        self.pan_offset = self.geometry["pan_offset"]
        self.tilt_offset = self.geometry["tilt_offset"]
        self.muzzle_offset = self.geometry["muzzle_offset"]
        self.pan_axis_sign = float(
            self.geometry["pan_axis_sign"]
        )
        self.tilt_axis_sign = float(
            self.geometry["tilt_axis_sign"]
        )
        self.pan_min = float(self.geometry["pan_min"])
        self.pan_max = float(self.geometry["pan_max"])
        self.tilt_min = float(self.geometry["tilt_min"])
        self.tilt_max = float(self.geometry["tilt_max"])

        discovered_clearance = self.discover_muzzle_clearance()
        if discovered_clearance is not None:
            self.muzzle_clearance = discovered_clearance

        self.gun_rate_publisher = self.create_publisher(
            GunRateCommand,
            "/backend/gun_rate_command",
            10,
        )
        self.fire_publisher = self.create_publisher(
            FireCommand,
            "/backend/fire_command",
            10,
        )
        self.status_publisher = self.create_publisher(
            String,
            "/test/auto_engage_status",
            10,
        )

        self.command_subscription = self.create_subscription(
            String,
            "/test/auto_engage_command",
            self.command_callback,
            10,
        )
        self.target_subscription = self.create_subscription(
            TargetPositionInfo,
            "/simulation/target_position",
            self.target_callback,
            10,
        )
        self.platform_position_subscription = self.create_subscription(
            PlatformPositionInfo,
            "/simulation/platform_position",
            self.platform_position_callback,
            10,
        )
        self.platform_velocity_subscription = self.create_subscription(
            PlatformVelocityInfo,
            "/simulation/platform_velocity",
            self.platform_velocity_callback,
            10,
        )
        self.stabilization_subscription = self.create_subscription(
            StabilizationData,
            "/simulation/stabilization_data",
            self.stabilization_callback,
            10,
        )
        self.gun_info_subscription = self.create_subscription(
            GunInfo,
            "/simulation/gun_info",
            self.gun_info_callback,
            10,
        )
        self.gun_status_subscription = self.create_subscription(
            GunStatusInfo,
            "/simulation/gun_status",
            self.gun_status_callback,
            10,
        )

        self.data_lock = threading.Lock()
        self.target: Optional[Dict[str, float]] = None
        self.platform_position: Optional[Dict[str, float]] = None
        self.platform_velocity: Optional[Dict[str, float]] = None
        self.stabilization: Optional[Dict[str, float]] = None
        self.gun_info: Optional[Dict[str, float]] = None
        self.gun_status: Optional[Dict[str, object]] = None

        self.previous_target: Optional[Dict[str, float]] = None
        self.target_velocity = {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        }

        self.active = False
        self.state = "IDLE"
        self.state_message = (
            "Phone test controller is idle. Backend path is untouched."
        )
        self.session_started_at: Optional[float] = None
        self.settle_started_at: Optional[float] = None
        self.muzzle_velocity = self.default_muzzle_velocity
        self.sequence = 0
        self.fire_sent = False
        self.aim_locked = False
        self.last_solution: Dict[str, object] = {}

        period = 1.0 / max(1.0, self.control_rate_hz)
        self.create_timer(period, self.control_loop)
        self.create_timer(0.5, self.publish_status)

        self.get_logger().info(
            "AUTO AIM ballistic v4 ready and IDLE. "
            "It publishes nothing until /test/auto_engage_command START."
        )
        self.get_logger().info(
            "Gun geometry source: "
            + str(self.geometry["source"])
        )
        self.get_logger().info(
            "Gun geometry | pan offset="
            f"{self.pan_offset} | tilt offset={self.tilt_offset} | "
            f"muzzle offset={self.muzzle_offset} | "
            f"clearance={self.muzzle_clearance:.3f} m"
        )
        self.get_logger().info(
            "The phone muzzle velocity is locked at START and "
            "used for both trajectory calculation and FireCommand."
        )

    @staticmethod
    def parse_pose(
        element,
    ) -> Tuple[float, float, float]:
        if element is None or not element.text:
            return (0.0, 0.0, 0.0)

        values = []
        for item in element.text.split():
            try:
                values.append(float(item))
            except ValueError:
                values.append(0.0)

        while len(values) < 3:
            values.append(0.0)

        return tuple(values[:3])

    @staticmethod
    def read_joint_axis_sign(
        root,
        joint_name: str,
        axis_index: int,
        fallback: float,
    ) -> float:
        joint = root.find(
            f".//joint[@name='{joint_name}']"
        )
        if joint is None:
            return fallback

        xyz_text = joint.findtext("axis/xyz") or ""
        try:
            values = [
                float(value)
                for value in xyz_text.split()
            ]
        except ValueError:
            return fallback

        while len(values) < 3:
            values.append(0.0)

        value = values[axis_index]
        if abs(value) < 0.5:
            return fallback
        return 1.0 if value > 0.0 else -1.0

    @staticmethod
    def read_joint_limits(
        root,
        joint_name: str,
        fallback_minimum: float,
        fallback_maximum: float,
    ) -> Tuple[float, float]:
        joint = root.find(
            f".//joint[@name='{joint_name}']"
        )
        if joint is None:
            return fallback_minimum, fallback_maximum

        try:
            minimum = float(
                joint.findtext("axis/limit/lower")
                or fallback_minimum
            )
            maximum = float(
                joint.findtext("axis/limit/upper")
                or fallback_maximum
            )
        except ValueError:
            return fallback_minimum, fallback_maximum

        if minimum >= maximum:
            return fallback_minimum, fallback_maximum
        return minimum, maximum

    def load_active_gun_geometry(self) -> Dict[str, object]:
        models_root = (
            Path.home()
            / "ball_launcher_ws"
            / "src"
            / "ball_launch_sim"
            / "models"
        )

        candidates = []

        if models_root.is_dir():
            for model_path in models_root.rglob("model.sdf"):
                try:
                    root = ET.parse(model_path).getroot()
                except (ET.ParseError, OSError):
                    continue

                pan_link = root.find(
                    ".//link[@name='pan_link']"
                )
                tilt_link = root.find(
                    ".//link[@name='tilt_link']"
                )
                muzzle_link = root.find(
                    ".//link[@name='muzzle_link']"
                )
                ship_link = root.find(
                    ".//link[@name='ship_link']"
                )

                if pan_link is None or tilt_link is None:
                    continue

                pan_offset = self.parse_pose(
                    pan_link.find("pose")
                )
                tilt_offset = self.parse_pose(
                    tilt_link.find("pose")
                )

                if muzzle_link is not None:
                    muzzle_offset = self.parse_pose(
                        muzzle_link.find("pose")
                    )
                else:
                    marker = root.find(
                        ".//visual[@name='muzzle_marker']/pose"
                    )
                    if marker is None:
                        continue
                    muzzle_offset = self.parse_pose(marker)

                score = (
                    abs(pan_offset[0]) * 10.0
                    + abs(pan_offset[2])
                    + abs(muzzle_offset[0])
                )

                path_lower = str(model_path).lower()
                if ship_link is not None:
                    score += 500.0
                if "heybeliada_ship" in path_lower:
                    score += 250.0
                if "float" in path_lower:
                    score += 30.0
                if "gun_test" in path_lower:
                    score -= 100.0

                pan_min, pan_max = self.read_joint_limits(
                    root,
                    "pan_joint",
                    -2.617994,
                    2.617994,
                )
                tilt_min, tilt_max = self.read_joint_limits(
                    root,
                    "tilt_joint",
                    -0.0872665,
                    1.2217305,
                )

                candidates.append({
                    "score": score,
                    "source": str(model_path),
                    "pan_offset": pan_offset,
                    "tilt_offset": tilt_offset,
                    "muzzle_offset": muzzle_offset,
                    "pan_axis_sign":
                        self.read_joint_axis_sign(
                            root,
                            "pan_joint",
                            2,
                            1.0,
                        ),
                    "tilt_axis_sign":
                        self.read_joint_axis_sign(
                            root,
                            "tilt_joint",
                            1,
                            -1.0,
                        ),
                    "pan_min": pan_min,
                    "pan_max": pan_max,
                    "tilt_min": tilt_min,
                    "tilt_max": tilt_max,
                })

        if candidates:
            candidates.sort(
                key=lambda item: float(item["score"]),
                reverse=True,
            )
            return candidates[0]

        self.get_logger().warning(
            "Active ship model geometry could not be read. "
            "Using the known Heybeliada fallback geometry."
        )
        return {
            "score": 0.0,
            "source": "Heybeliada fallback geometry",
            "pan_offset": (
                31.057680,
                0.0,
                6.183503,
            ),
            "tilt_offset": (
                0.113315,
                0.0,
                1.351354,
            ),
            "muzzle_offset": (
                5.35,
                0.0,
                0.0,
            ),
            "pan_axis_sign": 1.0,
            "tilt_axis_sign": -1.0,
            "pan_min": -2.617994,
            "pan_max": 2.617994,
            "tilt_min": -0.0872665,
            "tilt_max": 1.2217305,
        }

    @staticmethod
    def discover_muzzle_clearance() -> Optional[float]:
        launch_path = (
            Path.home()
            / "ball_launcher_ws"
            / "src"
            / "ball_launch_sim"
            / "launch"
            / "heybeliada_sydney_backend.launch.py"
        )

        try:
            text = launch_path.read_text(encoding="utf-8")
        except OSError:
            return None

        match = re.search(
            r"['\"]muzzle_clearance['\"]\s*:\s*"
            r"([-+]?[0-9]*\.?[0-9]+)",
            text,
        )
        if not match:
            return None

        try:
            value = float(match.group(1))
        except ValueError:
            return None

        if not math.isfinite(value) or value < 0.0:
            return None
        return value

    def next_sequence(self) -> int:
        self.sequence += 1
        return self.sequence

    @staticmethod
    def now_monotonic() -> float:
        return time.monotonic()

    def target_callback(self, message: TargetPositionInfo) -> None:
        now = self.now_monotonic()

        raw = {
            "x": float(message.position_x),
            "y": float(message.position_y),
            "z": float(message.position_z),
            "received": now,
            "target_id": str(message.target_id),
        }

        with self.data_lock:
            alpha_position = clamp(
                self.target_position_filter_alpha,
                0.0,
                1.0,
            )

            if self.target is None:
                current = dict(raw)
            else:
                current = {
                    "x": (
                        alpha_position * raw["x"]
                        + (1.0 - alpha_position)
                        * float(self.target["x"])
                    ),
                    "y": (
                        alpha_position * raw["y"]
                        + (1.0 - alpha_position)
                        * float(self.target["y"])
                    ),
                    "z": (
                        alpha_position * raw["z"]
                        + (1.0 - alpha_position)
                        * float(self.target["z"])
                    ),
                    "received": now,
                    "target_id": raw["target_id"],
                }

            previous = self.previous_target

            if previous is not None:
                delta_time = (
                    now - float(previous["received"])
                )

                if 0.01 <= delta_time <= 2.0:
                    raw_velocity = {
                        "x": (
                            current["x"] - previous["x"]
                        ) / delta_time,
                        "y": (
                            current["y"] - previous["y"]
                        ) / delta_time,
                        "z": (
                            current["z"] - previous["z"]
                        ) / delta_time,
                    }

                    alpha_velocity = clamp(
                        self.velocity_filter_alpha,
                        0.0,
                        1.0,
                    )

                    for axis in ("x", "y", "z"):
                        self.target_velocity[axis] = (
                            alpha_velocity
                            * raw_velocity[axis]
                            + (1.0 - alpha_velocity)
                            * self.target_velocity[axis]
                        )

            self.previous_target = dict(current)
            self.target = current

    def platform_position_callback(
        self,
        message: PlatformPositionInfo,
    ) -> None:
        with self.data_lock:
            self.platform_position = {
                "x": float(message.position_x),
                "y": float(message.position_y),
                "z": float(message.position_z),
                "received": self.now_monotonic(),
            }

    def platform_velocity_callback(
        self,
        message: PlatformVelocityInfo,
    ) -> None:
        with self.data_lock:
            self.platform_velocity = {
                "x": float(message.velocity_x),
                "y": float(message.velocity_y),
                "z": float(message.velocity_z),
                "received": self.now_monotonic(),
            }

    def stabilization_callback(
        self,
        message: StabilizationData,
    ) -> None:
        with self.data_lock:
            self.stabilization = {
                "roll": float(message.roll),
                "pitch": float(message.pitch),
                "yaw": float(message.yaw),
                "roll_rate": float(message.roll_rate),
                "pitch_rate": float(message.pitch_rate),
                "yaw_rate": float(message.yaw_rate),
                "received": self.now_monotonic(),
            }

    def gun_info_callback(self, message: GunInfo) -> None:
        with self.data_lock:
            self.gun_info = {
                "pan_angle": float(message.pan_angle),
                "tilt_angle": float(message.tilt_angle),
                "pan_rate": float(message.pan_rate),
                "tilt_rate": float(message.tilt_rate),
                "received": self.now_monotonic(),
            }

    def gun_status_callback(self, message: GunStatusInfo) -> None:
        with self.data_lock:
            self.gun_status = {
                "control_enabled": bool(message.control_enabled),
                "ready_to_fire": bool(message.ready_to_fire),
                "firing": bool(message.firing),
                "fault": bool(message.fault),
                "fault_text": str(message.fault_text),
                "received": self.now_monotonic(),
            }

    def command_callback(self, message: String) -> None:
        raw = message.data.strip()
        action = raw.upper()
        payload: Dict[str, object] = {}

        if raw.startswith("{"):
            try:
                payload = json.loads(raw)
                action = str(
                    payload.get("action", "")
                ).strip().upper()
            except json.JSONDecodeError:
                self.abort("Invalid AUTO AIM command JSON.")
                return

        if action == "START":
            velocity = float(
                payload.get(
                    "muzzle_velocity",
                    self.default_muzzle_velocity,
                )
            )
            if not math.isfinite(velocity) or velocity <= 0.0:
                self.abort("Muzzle velocity must be positive.")
                return

            self.muzzle_velocity = velocity
            self.active = True
            self.fire_sent = False
            self.aim_locked = False
            self.session_started_at = self.now_monotonic()
            self.settle_started_at = None
            self.state = "ACQUIRE"
            self.state_message = (
                "Acquiring telemetry. Ballistic and fire speed "
                f"locked to {self.muzzle_velocity:.2f} m/s."
            )
            self.last_solution = {}
            self.publish_status()
            self.get_logger().warning(
                "PHONE TEST AUTO AIM started. "
                "Do not send backend/manual gun commands simultaneously."
            )
            return

        if action == "CANCEL":
            self.cancel("Cancelled from phone.")
            return

        self.abort(f"Unknown AUTO AIM command: {action!r}")

    def cancel(self, reason: str) -> None:
        self.publish_stop()
        self.active = False
        self.fire_sent = False
        self.aim_locked = False
        self.settle_started_at = None
        self.state = "CANCELLED"
        self.state_message = reason
        self.publish_status()

    def abort(self, reason: str) -> None:
        self.publish_stop()
        self.active = False
        self.fire_sent = False
        self.aim_locked = False
        self.settle_started_at = None
        self.state = "ABORTED"
        self.state_message = reason
        self.publish_status()
        self.get_logger().error(reason)

    def telemetry_snapshot(
        self,
    ) -> Tuple[Optional[Dict[str, object]], Optional[str]]:
        now = self.now_monotonic()

        with self.data_lock:
            values = {
                "target": dict(self.target) if self.target else None,
                "platform_position": (
                    dict(self.platform_position)
                    if self.platform_position
                    else None
                ),
                "platform_velocity": (
                    dict(self.platform_velocity)
                    if self.platform_velocity
                    else None
                ),
                "stabilization": (
                    dict(self.stabilization)
                    if self.stabilization
                    else None
                ),
                "gun_info": (
                    dict(self.gun_info)
                    if self.gun_info
                    else None
                ),
                "gun_status": (
                    dict(self.gun_status)
                    if self.gun_status
                    else None
                ),
                "target_velocity": dict(self.target_velocity),
            }

        required = (
            "target",
            "platform_position",
            "stabilization",
            "gun_info",
        )

        for key in required:
            item = values[key]
            if item is None:
                return None, f"Waiting for {key} telemetry."

            age = now - float(item["received"])
            if age > self.telemetry_timeout:
                return None, (
                    f"{key} telemetry is stale "
                    f"({age:.2f} seconds)."
                )

        if values["platform_velocity"] is None:
            values["platform_velocity"] = {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
                "received": now,
            }

        return values, None

    def control_loop(self) -> None:
        if not self.active:
            return

        now = self.now_monotonic()

        if (
            self.session_started_at is not None
            and now - self.session_started_at > self.overall_timeout
        ):
            self.abort("AUTO AIM timeout.")
            return

        telemetry, error = self.telemetry_snapshot()
        if telemetry is None:
            self.state = "ACQUIRE"
            self.state_message = error or "Waiting for telemetry."
            return

        gun_status = telemetry.get("gun_status")
        if (
            gun_status is not None
            and bool(gun_status["fault"])
        ):
            fault_text = str(
                gun_status["fault_text"]
            ).strip()
            self.abort(
                "Gun fault"
                + (f": {fault_text}" if fault_text else ".")
            )
            return

        solution = self.solve_solution(telemetry)
        if solution is None:
            self.abort(
                "No ballistic solution for the current target "
                "and muzzle velocity."
            )
            return

        gun_info = telemetry["gun_info"]
        stabilization = telemetry["stabilization"]

        pan_error = wrap_angle(
            float(solution["desired_pan"])
            - float(gun_info["pan_angle"])
        )
        tilt_error = (
            float(solution["desired_tilt"])
            - float(gun_info["tilt_angle"])
        )

        pan_command = clamp(
            self.pan_kp * pan_error,
            -self.max_pan_rate,
            self.max_pan_rate,
        )
        tilt_command = clamp(
            self.tilt_kp * tilt_error,
            -self.max_tilt_rate,
            self.max_tilt_rate,
        )

        # Nişan ilk kez normal tolerans içinde yakalanır.
        # Kilitlendikten sonra hata release toleransını aşmadıkça
        # küçük sağ-sol düzeltmeler yeniden başlatılmaz.
        if self.aim_locked:
            within_aim_tolerance = (
                abs(pan_error)
                <= self.pan_release_tolerance
                and abs(tilt_error)
                <= self.tilt_release_tolerance
            )
        else:
            within_aim_tolerance = (
                abs(pan_error) <= self.pan_tolerance
                and abs(tilt_error)
                <= self.tilt_tolerance
            )

        self.aim_locked = within_aim_tolerance
        gun_is_slow = (
            abs(float(gun_info["pan_rate"]))
            <= self.gun_rate_tolerance
            and abs(float(gun_info["tilt_rate"]))
            <= self.gun_rate_tolerance
        )
        platform_is_stable = (
            abs(float(stabilization["roll_rate"]))
            <= self.platform_rate_tolerance
            and abs(float(stabilization["pitch_rate"]))
            <= self.platform_rate_tolerance
            and abs(float(stabilization["yaw_rate"]))
            <= self.platform_rate_tolerance
        )
        ready_to_fire = (
            bool(gun_status["ready_to_fire"])
            if gun_status is not None
            else True
        )

        self.last_solution = {
            **solution,
            "pan_error_deg": math.degrees(pan_error),
            "tilt_error_deg": math.degrees(tilt_error),
            "pan_command": pan_command,
            "tilt_command": tilt_command,
            "gun_is_slow": gun_is_slow,
            "platform_is_stable": platform_is_stable,
            "ready_to_fire": ready_to_fire,
        }

        if within_aim_tolerance:
            self.publish_stop()

            all_fire_conditions = (
                gun_is_slow
                and platform_is_stable
                and ready_to_fire
            )

            if not all_fire_conditions:
                self.settle_started_at = None
                self.state = "WAIT_SAFE"
                conditions = []
                if not gun_is_slow:
                    conditions.append("gun rate")
                if not platform_is_stable:
                    conditions.append("platform stability")
                if not ready_to_fire:
                    conditions.append("ready_to_fire")
                self.state_message = (
                    "Aim reached; waiting for "
                    + ", ".join(conditions)
                    + "."
                )
                return

            if self.settle_started_at is None:
                self.settle_started_at = now
                self.state = "SETTLING"
                self.state_message = "Aim reached; settling."
                return

            elapsed = now - self.settle_started_at
            if elapsed < self.settle_time:
                self.state = "SETTLING"
                self.state_message = (
                    f"Settling: {elapsed:.2f}/{self.settle_time:.2f} s."
                )
                return

            if not self.fire_sent:
                self.publish_fire()
                self.fire_sent = True
                self.active = False
                self.state = "COMPLETE"
                self.state_message = (
                    "Fire command sent once through "
                    "/backend/fire_command."
                )
                self.publish_status()
            return

        self.settle_started_at = None
        self.state = "TRACKING"
        self.state_message = (
            "Tracking target. "
            f"Pan error {math.degrees(pan_error):.2f}°, "
            f"tilt error {math.degrees(tilt_error):.2f}°."
        )
        self.publish_gun_rate(pan_command, tilt_command)

    def publish_gun_rate(
        self,
        pan_rate: float,
        tilt_rate: float,
    ) -> None:
        message = GunRateCommand()
        message.sequence = self.next_sequence()
        message.pan_rate = float(pan_rate)
        message.tilt_rate = float(tilt_rate)
        message.control_enabled = True
        message.timestamp = self.get_clock().now().to_msg()
        self.gun_rate_publisher.publish(message)

    def publish_stop(self) -> None:
        self.publish_gun_rate(0.0, 0.0)

    def publish_fire(self) -> None:
        message = FireCommand()
        message.sequence = self.next_sequence()
        message.muzzle_velocity = float(self.muzzle_velocity)
        message.timestamp = self.get_clock().now().to_msg()
        self.fire_publisher.publish(message)

    def muzzle_world_pose(
        self,
        platform_position: Tuple[float, float, float],
        platform_rotation,
        pan_angle: float,
        tilt_angle: float,
    ):
        pan_rotation = rotation_z(
            self.pan_axis_sign * pan_angle
        )
        tilt_rotation = rotation_y(
            self.tilt_axis_sign * tilt_angle
        )
        joint_rotation = matrix_multiply(
            pan_rotation,
            tilt_rotation,
        )

        muzzle_with_clearance = (
            float(self.muzzle_offset[0])
            + self.muzzle_clearance,
            float(self.muzzle_offset[1]),
            float(self.muzzle_offset[2]),
        )

        tilt_to_muzzle = matrix_vector_multiply(
            tilt_rotation,
            muzzle_with_clearance,
        )
        pan_to_muzzle = vector_add(
            self.tilt_offset,
            tilt_to_muzzle,
        )
        model_muzzle = vector_add(
            self.pan_offset,
            matrix_vector_multiply(
                pan_rotation,
                pan_to_muzzle,
            ),
        )

        world_muzzle = vector_add(
            platform_position,
            matrix_vector_multiply(
                platform_rotation,
                model_muzzle,
            ),
        )

        model_direction = matrix_vector_multiply(
            joint_rotation,
            (1.0, 0.0, 0.0),
        )
        world_direction = matrix_vector_multiply(
            platform_rotation,
            model_direction,
        )

        direction_length = vector_length(world_direction)
        if direction_length <= 1e-9:
            raise RuntimeError("Invalid muzzle direction.")

        world_direction = vector_scale(
            world_direction,
            1.0 / direction_length,
        )
        return world_muzzle, world_direction

    def low_arc_world_pitch(
        self,
        horizontal_range: float,
        vertical_difference: float,
        speed: float,
    ) -> Optional[float]:
        if horizontal_range <= 1e-6 or speed <= 0.0:
            return None

        speed_squared = speed * speed
        discriminant = (
            speed_squared * speed_squared
            - self.gravity
            * (
                self.gravity
                * horizontal_range
                * horizontal_range
                + 2.0
                * vertical_difference
                * speed_squared
            )
        )

        if discriminant < 0.0:
            return None

        denominator = (
            self.gravity * horizontal_range
        )
        if abs(denominator) <= 1e-9:
            return None

        return math.atan2(
            speed_squared - math.sqrt(discriminant),
            denominator,
        )

    def solve_solution(
        self,
        telemetry: Dict[str, object],
    ) -> Optional[Dict[str, float]]:
        target = telemetry["target"]
        platform = telemetry["platform_position"]
        platform_velocity = telemetry["platform_velocity"]
        stabilization = telemetry["stabilization"]
        target_velocity = telemetry["target_velocity"]

        speed = float(self.muzzle_velocity)
        if not math.isfinite(speed) or speed <= 0.0:
            return None

        platform_velocity_vector = (
            float(platform_velocity["x"]),
            float(platform_velocity["y"]),
            float(platform_velocity["z"]),
        )
        target_velocity_vector = (
            float(target_velocity["x"]),
            float(target_velocity["y"]),
            float(target_velocity["z"]),
        )

        current_platform_position = (
            float(platform["x"]),
            float(platform["y"]),
            float(platform["z"]),
        )

        launch_platform_position = vector_add(
            current_platform_position,
            vector_scale(
                platform_velocity_vector,
                self.fire_latency,
            ),
        )

        launch_roll = (
            float(stabilization["roll"])
            + float(stabilization["roll_rate"])
            * self.fire_latency
        )
        launch_pitch = (
            float(stabilization["pitch"])
            + float(stabilization["pitch_rate"])
            * self.fire_latency
        )
        launch_yaw = (
            float(stabilization["yaw"])
            + float(stabilization["yaw_rate"])
            * self.fire_latency
        )

        platform_rotation = rotation_from_rpy(
            launch_roll,
            launch_pitch,
            launch_yaw,
        )
        inverse_platform_rotation = matrix_transpose(
            platform_rotation
        )

        target_at_launch = (
            float(target["x"])
            + target_velocity_vector[0]
            * self.fire_latency,
            float(target["y"])
            + target_velocity_vector[1]
            * self.fire_latency,
            float(target["z"])
            + self.target_aim_offset_z
            + target_velocity_vector[2]
            * self.fire_latency,
        )

        inherited_velocity = (
            platform_velocity_vector
            if self.projectile_inherits_platform_velocity
            else (0.0, 0.0, 0.0)
        )

        turret_origin = vector_add(
            launch_platform_position,
            matrix_vector_multiply(
                platform_rotation,
                self.pan_offset,
            ),
        )
        initial_vector = vector_subtract(
            target_at_launch,
            turret_origin,
        )
        initial_local = matrix_vector_multiply(
            inverse_platform_rotation,
            initial_vector,
        )

        geometric_bearing = math.atan2(
            initial_local[1],
            initial_local[0],
        )
        geometric_elevation = math.atan2(
            initial_local[2],
            math.hypot(
                initial_local[0],
                initial_local[1],
            ),
        )

        pan_angle = (
            geometric_bearing / self.pan_axis_sign
        )
        tilt_angle = (
            -geometric_elevation / self.tilt_axis_sign
        )

        pan_angle = clamp(
            pan_angle,
            self.pan_min,
            self.pan_max,
        )
        tilt_angle = clamp(
            tilt_angle,
            self.tilt_min,
            self.tilt_max,
        )

        initial_distance = vector_length(initial_vector)
        if initial_distance < self.minimum_range:
            return None

        flight_time = max(
            0.05,
            initial_distance / speed,
        )

        predicted_target = target_at_launch
        world_direction = (1.0, 0.0, 0.0)
        muzzle_position = launch_platform_position

        for _ in range(30):
            predicted_target = vector_add(
                target_at_launch,
                vector_scale(
                    target_velocity_vector,
                    flight_time,
                ),
            )

            effective_target = vector_subtract(
                predicted_target,
                vector_scale(
                    inherited_velocity,
                    flight_time,
                ),
            )

            muzzle_position, _ = self.muzzle_world_pose(
                launch_platform_position,
                platform_rotation,
                pan_angle,
                tilt_angle,
            )

            displacement = vector_subtract(
                effective_target,
                muzzle_position,
            )
            horizontal_range = math.hypot(
                displacement[0],
                displacement[1],
            )
            if horizontal_range < self.minimum_range:
                return None

            world_pitch = self.low_arc_world_pitch(
                horizontal_range,
                displacement[2],
                speed,
            )
            if world_pitch is None:
                return None

            world_yaw = math.atan2(
                displacement[1],
                displacement[0],
            )
            world_direction = (
                math.cos(world_pitch)
                * math.cos(world_yaw),
                math.cos(world_pitch)
                * math.sin(world_yaw),
                math.sin(world_pitch),
            )

            local_direction = matrix_vector_multiply(
                inverse_platform_rotation,
                world_direction,
            )
            local_bearing = math.atan2(
                local_direction[1],
                local_direction[0],
            )
            local_elevation = math.atan2(
                local_direction[2],
                math.hypot(
                    local_direction[0],
                    local_direction[1],
                ),
            )

            new_pan_angle = (
                local_bearing / self.pan_axis_sign
            )
            new_tilt_angle = (
                -local_elevation / self.tilt_axis_sign
            )

            if (
                new_pan_angle < self.pan_min
                or new_pan_angle > self.pan_max
                or new_tilt_angle < self.tilt_min
                or new_tilt_angle > self.tilt_max
            ):
                return None

            new_muzzle_position, new_world_direction = (
                self.muzzle_world_pose(
                    launch_platform_position,
                    platform_rotation,
                    new_pan_angle,
                    new_tilt_angle,
                )
            )

            new_displacement = vector_subtract(
                effective_target,
                new_muzzle_position,
            )
            horizontal_speed = (
                speed
                * math.hypot(
                    new_world_direction[0],
                    new_world_direction[1],
                )
            )
            new_horizontal_range = math.hypot(
                new_displacement[0],
                new_displacement[1],
            )

            if horizontal_speed <= 1e-6:
                return None

            new_flight_time = (
                new_horizontal_range / horizontal_speed
            )

            converged = (
                abs(new_flight_time - flight_time) < 1e-5
                and abs(new_pan_angle - pan_angle) < 1e-7
                and abs(new_tilt_angle - tilt_angle) < 1e-7
            )

            pan_angle = new_pan_angle
            tilt_angle = new_tilt_angle
            flight_time = new_flight_time
            muzzle_position = new_muzzle_position
            world_direction = new_world_direction

            if converged:
                break

        predicted_target = vector_add(
            target_at_launch,
            vector_scale(
                target_velocity_vector,
                flight_time,
            ),
        )

        projectile_velocity = vector_add(
            inherited_velocity,
            vector_scale(world_direction, speed),
        )

        predicted_impact = (
            muzzle_position[0]
            + projectile_velocity[0] * flight_time,
            muzzle_position[1]
            + projectile_velocity[1] * flight_time,
            muzzle_position[2]
            + projectile_velocity[2] * flight_time
            - 0.5
            * self.gravity
            * flight_time
            * flight_time,
        )

        miss_vector = vector_subtract(
            predicted_impact,
            predicted_target,
        )
        predicted_miss = vector_length(miss_vector)

        return {
            "desired_pan": pan_angle,
            "desired_tilt": tilt_angle,
            "horizontal_range": math.hypot(
                predicted_target[0] - muzzle_position[0],
                predicted_target[1] - muzzle_position[1],
            ),
            "flight_time": flight_time,
            "predicted_x": predicted_target[0],
            "predicted_y": predicted_target[1],
            "predicted_z": predicted_target[2],
            "impact_x": predicted_impact[0],
            "impact_y": predicted_impact[1],
            "impact_z": predicted_impact[2],
            "muzzle_world_x": muzzle_position[0],
            "muzzle_world_y": muzzle_position[1],
            "muzzle_world_z": muzzle_position[2],
            "target_speed": vector_length(
                target_velocity_vector
            ),
            "solution_muzzle_velocity": speed,
            "target_aim_offset_z":
                self.target_aim_offset_z,
            "predicted_miss_m": predicted_miss,
            "geometry_source":
                str(self.geometry["source"]),
            "muzzle_clearance":
                self.muzzle_clearance,
        }

    def publish_status(self) -> None:
        payload: Dict[str, object] = {
            "state": self.state,
            "active": self.active,
            "message": self.state_message,
            "fire_sent": self.fire_sent,
            "muzzle_velocity": self.muzzle_velocity,
            "solution_muzzle_velocity":
                self.muzzle_velocity,
            "target_aim_offset_z":
                self.target_aim_offset_z,
            "geometry_source":
                str(self.geometry["source"]),
            "muzzle_clearance":
                self.muzzle_clearance,
            "backend_safe": True,
            "timestamp": time.time(),
        }
        payload.update(self.last_solution)

        message = String()
        message.data = json.dumps(
            payload,
            ensure_ascii=False,
        )
        self.status_publisher.publish(message)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AutoEngagementTestController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.cancel("Controller shutting down.")
        except Exception:
            pass

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
