#!/usr/bin/env python3

import math
import time
from typing import Optional

import rclpy
from naval_interfaces.msg import GunRateCommand
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float64


class GunRateController(Node):
    """
    Backend'den gelen açısal hız komutlarını pan/tilt konum
    hedeflerine dönüştürür.

    Ateş komutu doğrudan uygulanmaz. Önce kuyruğa alınır ve:

    - Komut edilen top hızları durduğunda,
    - Gazebo'dan gelen gerçek joint hızları durduğunda,
    - Gerçek açılar hedef açılara ulaştığında,
    - Sistem belirlenen süre boyunca kararlı kaldığında,
    - İleride platform kararlılık izni verildiğinde,

    /simulation/fire_request yayımlanır.
    """

    PAN_MIN_RAD = -2.617994
    PAN_MAX_RAD = 2.617994

    TILT_MIN_RAD = -0.0872665
    TILT_MAX_RAD = 1.2217305

    DEFAULT_MAX_PAN_RATE_RAD_S = 0.35
    DEFAULT_MAX_TILT_RATE_RAD_S = 0.20

    def __init__(self) -> None:
        super().__init__('gun_rate_controller')

        # Mevcut hareket parametreleri.
        self.declare_parameter(
            'max_pan_rate_rad_s',
            self.DEFAULT_MAX_PAN_RATE_RAD_S,
        )
        self.declare_parameter(
            'max_tilt_rate_rad_s',
            self.DEFAULT_MAX_TILT_RATE_RAD_S,
        )
        self.declare_parameter(
            'watchdog_timeout_sec',
            0.5,
        )
        self.declare_parameter(
            'control_period_sec',
            0.02,
        )
        self.declare_parameter(
            'initial_pan_rad',
            0.0,
        )
        self.declare_parameter(
            'initial_tilt_rad',
            0.0,
        )

        # Ateş güvenlik parametreleri.
        self.declare_parameter(
            'command_stop_threshold_rad_s',
            0.005,
        )
        self.declare_parameter(
            'joint_stop_threshold_rad_s',
            0.015,
        )
        self.declare_parameter(
            'position_tolerance_rad',
            0.010,
        )
        self.declare_parameter(
            'settle_time_sec',
            0.40,
        )
        self.declare_parameter(
            'joint_state_timeout_sec',
            0.50,
        )

        # Gelecekte roll, pitch ve gemi hareketi için.
        self.declare_parameter(
            'require_platform_stable',
            False,
        )
        self.declare_parameter(
            'platform_stability_timeout_sec',
            0.50,
        )

        self.max_pan_rate = float(
            self.get_parameter(
                'max_pan_rate_rad_s'
            ).value
        )
        self.max_tilt_rate = float(
            self.get_parameter(
                'max_tilt_rate_rad_s'
            ).value
        )
        self.watchdog_timeout = float(
            self.get_parameter(
                'watchdog_timeout_sec'
            ).value
        )
        self.control_period = float(
            self.get_parameter(
                'control_period_sec'
            ).value
        )

        self.command_stop_threshold = float(
            self.get_parameter(
                'command_stop_threshold_rad_s'
            ).value
        )
        self.joint_stop_threshold = float(
            self.get_parameter(
                'joint_stop_threshold_rad_s'
            ).value
        )
        self.position_tolerance = float(
            self.get_parameter(
                'position_tolerance_rad'
            ).value
        )
        self.settle_time = float(
            self.get_parameter(
                'settle_time_sec'
            ).value
        )
        self.joint_state_timeout = float(
            self.get_parameter(
                'joint_state_timeout_sec'
            ).value
        )

        self.require_platform_stable = bool(
            self.get_parameter(
                'require_platform_stable'
            ).value
        )
        self.platform_stability_timeout = float(
            self.get_parameter(
                'platform_stability_timeout_sec'
            ).value
        )

        self.current_pan = self._clamp(
            float(
                self.get_parameter(
                    'initial_pan_rad'
                ).value
            ),
            self.PAN_MIN_RAD,
            self.PAN_MAX_RAD,
        )
        self.current_tilt = self._clamp(
            float(
                self.get_parameter(
                    'initial_tilt_rad'
                ).value
            ),
            self.TILT_MIN_RAD,
            self.TILT_MAX_RAD,
        )

        # Backend tarafından istenen hareket hızları.
        self.commanded_pan_rate = 0.0
        self.commanded_tilt_rate = 0.0

        # Controller'ın konum hedefini ne hızla değiştirdiği.
        self.applied_pan_rate = 0.0
        self.applied_tilt_rate = 0.0

        # Gazebo'dan ölçülen gerçek top durumu.
        self.actual_pan: Optional[float] = None
        self.actual_tilt: Optional[float] = None

        self.actual_pan_rate = 0.0
        self.actual_tilt_rate = 0.0

        self.last_joint_state_time: Optional[float] = None

        self.control_enabled = False
        self.previous_fire = False

        # Ateş isteği burada bekletilir.
        self.fire_pending = False
        self.stable_since: Optional[float] = None
        self.ready_to_fire = False

        # Gelecekte gemi hareket ve roll/pitch kontrolü.
        self.platform_stable = False
        self.last_platform_stability_time: Optional[float] = None

        self.last_command_time: Optional[float] = None
        self.last_update_time = time.monotonic()
        self.watchdog_active = False

        # Backend komutları.
        self.command_subscription = self.create_subscription(
            GunRateCommand,
            '/backend/gun_rate_command',
            self.command_callback,
            10,
        )

        # Gazebo gerçek joint durumları.
        self.joint_state_subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10,
        )

        # Gelecekte platform hareket izni.
        self.platform_stable_subscription = self.create_subscription(
            Bool,
            '/simulation/platform_stable',
            self.platform_stable_callback,
            10,
        )

        # Eski ROS topic'leri.
        self.pan_publisher = self.create_publisher(
            Float64,
            '/pan_cmd',
            10,
        )
        self.tilt_publisher = self.create_publisher(
            Float64,
            '/tilt_cmd',
            10,
        )

        # Heybeliada Gazebo model topic'leri.
        self.ship_pan_publisher = self.create_publisher(
            Float64,
            '/heybeliada/pan_cmd',
            10,
        )
        self.ship_tilt_publisher = self.create_publisher(
            Float64,
            '/heybeliada/tilt_cmd',
            10,
        )

        # Gerçek ateşleme çıkışı.
        self.fire_request_publisher = self.create_publisher(
            Bool,
            '/simulation/fire_request',
            10,
        )

        # İzleme ve telemetri için.
        self.ready_publisher = self.create_publisher(
            Bool,
            '/simulation/ready_to_fire',
            10,
        )
        self.fire_pending_publisher = self.create_publisher(
            Bool,
            '/simulation/fire_pending',
            10,
        )

        self.control_timer = self.create_timer(
            self.control_period,
            self.control_loop,
        )

        self.get_logger().info(
            'Gun rate controller started with fire interlock.'
        )
        self.get_logger().info(
            'Fire commands are queued until gun motion settles.'
        )
        self.get_logger().info(
            'Joint state input: /joint_states'
        )
        self.get_logger().info(
            'Ready output: /simulation/ready_to_fire'
        )
        self.get_logger().info(
            'Platform stability required: '
            f'{self.require_platform_stable}'
        )

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        return max(
            minimum,
            min(maximum, value),
        )

    @staticmethod
    def _joint_index(
        names,
        required_name: str,
    ) -> Optional[int]:
        """
        Hem pan_joint hem de model::pan_joint biçimlerini destekler.
        """

        for index, name in enumerate(names):
            if name == required_name:
                return index

            if name.endswith(
                f'::{required_name}'
            ):
                return index

            if name.endswith(
                f'/{required_name}'
            ):
                return index

        return None

    def command_callback(
        self,
        message: GunRateCommand,
    ) -> None:
        now = time.monotonic()

        if not math.isfinite(
            message.pan_rate_rad_s
        ):
            self.get_logger().error(
                'Rejected command: pan rate is not finite.'
            )
            return

        if not math.isfinite(
            message.tilt_rate_rad_s
        ):
            self.get_logger().error(
                'Rejected command: tilt rate is not finite.'
            )
            return

        self.last_command_time = now
        self.watchdog_active = False

        self.control_enabled = bool(
            message.control_enabled
        )

        if self.control_enabled:
            self.commanded_pan_rate = self._clamp(
                float(message.pan_rate_rad_s),
                -self.max_pan_rate,
                self.max_pan_rate,
            )
            self.commanded_tilt_rate = self._clamp(
                float(message.tilt_rate_rad_s),
                -self.max_tilt_rate,
                self.max_tilt_rate,
            )
        else:
            self.commanded_pan_rate = 0.0
            self.commanded_tilt_rate = 0.0

            if self.fire_pending:
                self.get_logger().warning(
                    'Pending fire request cancelled because '
                    'control was disabled.'
                )

            self.fire_pending = False
            self.stable_since = None

        fire_requested = bool(message.fire)

        # Fire, false -> true geçişinde yalnızca kuyruğa alınır.
        if (
            self.control_enabled
            and fire_requested
            and not self.previous_fire
        ):
            self.fire_pending = True
            self.stable_since = None

            self.get_logger().info(
                'Fire request queued. Waiting for gun to settle.'
            )

        self.previous_fire = (
            fire_requested
            if self.control_enabled
            else False
        )

    def joint_state_callback(
        self,
        message: JointState,
    ) -> None:
        now = time.monotonic()

        pan_index = self._joint_index(
            message.name,
            'pan_joint',
        )
        tilt_index = self._joint_index(
            message.name,
            'tilt_joint',
        )

        previous_pan = self.actual_pan
        previous_tilt = self.actual_tilt
        previous_time = self.last_joint_state_time

        if (
            pan_index is not None
            and pan_index < len(message.position)
        ):
            value = float(
                message.position[pan_index]
            )

            if math.isfinite(value):
                self.actual_pan = value

        if (
            tilt_index is not None
            and tilt_index < len(message.position)
        ):
            value = float(
                message.position[tilt_index]
            )

            if math.isfinite(value):
                self.actual_tilt = value

        delta_time = None

        if previous_time is not None:
            delta_time = now - previous_time

        # Gazebo velocity alanı varsa doğrudan kullan.
        if (
            pan_index is not None
            and pan_index < len(message.velocity)
            and math.isfinite(
                float(message.velocity[pan_index])
            )
        ):
            self.actual_pan_rate = float(
                message.velocity[pan_index]
            )
        elif (
            delta_time is not None
            and delta_time > 1e-6
            and previous_pan is not None
            and self.actual_pan is not None
        ):
            self.actual_pan_rate = (
                self.actual_pan - previous_pan
            ) / delta_time

        if (
            tilt_index is not None
            and tilt_index < len(message.velocity)
            and math.isfinite(
                float(message.velocity[tilt_index])
            )
        ):
            self.actual_tilt_rate = float(
                message.velocity[tilt_index]
            )
        elif (
            delta_time is not None
            and delta_time > 1e-6
            and previous_tilt is not None
            and self.actual_tilt is not None
        ):
            self.actual_tilt_rate = (
                self.actual_tilt - previous_tilt
            ) / delta_time

        if (
            self.actual_pan is not None
            or self.actual_tilt is not None
        ):
            self.last_joint_state_time = now

    def platform_stable_callback(
        self,
        message: Bool,
    ) -> None:
        self.platform_stable = bool(
            message.data
        )
        self.last_platform_stability_time = (
            time.monotonic()
        )

    def apply_watchdog(
        self,
        now: float,
    ) -> None:
        if self.last_command_time is None:
            return

        command_age = (
            now - self.last_command_time
        )

        if command_age <= self.watchdog_timeout:
            return

        self.commanded_pan_rate = 0.0
        self.commanded_tilt_rate = 0.0
        self.control_enabled = False
        self.previous_fire = False

        # Haberleşme kesilince bekleyen atış kesinlikle yapılmaz.
        self.fire_pending = False
        self.stable_since = None
        self.ready_to_fire = False

        if not self.watchdog_active:
            self.get_logger().warning(
                'Command watchdog timeout. '
                'Gun motion stopped and pending fire cancelled.'
            )
            self.watchdog_active = True

    def platform_is_ready(
        self,
        now: float,
    ) -> bool:
        # Şimdilik platform kontrolü kapalı.
        if not self.require_platform_stable:
            return True

        if self.last_platform_stability_time is None:
            return False

        message_age = (
            now
            - self.last_platform_stability_time
        )

        if (
            message_age
            > self.platform_stability_timeout
        ):
            return False

        return self.platform_stable

    def gun_is_stopped(
        self,
        now: float,
    ) -> bool:
        if not self.control_enabled:
            return False

        if self.last_joint_state_time is None:
            return False

        joint_state_age = (
            now - self.last_joint_state_time
        )

        if (
            joint_state_age
            > self.joint_state_timeout
        ):
            return False

        if (
            self.actual_pan is None
            or self.actual_tilt is None
        ):
            return False

        command_stopped = (
            abs(self.commanded_pan_rate)
            <= self.command_stop_threshold
            and
            abs(self.commanded_tilt_rate)
            <= self.command_stop_threshold
        )

        real_motion_stopped = (
            abs(self.actual_pan_rate)
            <= self.joint_stop_threshold
            and
            abs(self.actual_tilt_rate)
            <= self.joint_stop_threshold
        )

        pan_error = abs(
            self.actual_pan - self.current_pan
        )
        tilt_error = abs(
            self.actual_tilt - self.current_tilt
        )

        position_reached = (
            pan_error <= self.position_tolerance
            and
            tilt_error <= self.position_tolerance
        )

        return (
            command_stopped
            and real_motion_stopped
            and position_reached
            and self.platform_is_ready(now)
        )

    def update_fire_interlock(
        self,
        now: float,
    ) -> None:
        stable_now = self.gun_is_stopped(
            now
        )

        if stable_now:
            if self.stable_since is None:
                self.stable_since = now
        else:
            self.stable_since = None

        self.ready_to_fire = (
            self.stable_since is not None
            and
            now - self.stable_since
            >= self.settle_time
        )

        ready_message = Bool()
        ready_message.data = self.ready_to_fire
        self.ready_publisher.publish(
            ready_message
        )

        pending_message = Bool()
        pending_message.data = self.fire_pending
        self.fire_pending_publisher.publish(
            pending_message
        )

        if (
            not self.fire_pending
            or not self.ready_to_fire
        ):
            return

        fire_message = Bool()
        fire_message.data = True

        self.fire_request_publisher.publish(
            fire_message
        )

        self.fire_pending = False

        self.get_logger().info(
            'FIRE: gun motion finished and '
            'the system remained stable for '
            f'{self.settle_time:.2f} seconds.'
        )

    def control_loop(self) -> None:
        now = time.monotonic()

        delta_time = (
            now - self.last_update_time
        )
        self.last_update_time = now

        delta_time = self._clamp(
            delta_time,
            0.0,
            0.1,
        )

        self.apply_watchdog(now)

        previous_pan = self.current_pan
        previous_tilt = self.current_tilt

        requested_pan = (
            self.current_pan
            + self.commanded_pan_rate
            * delta_time
        )
        requested_tilt = (
            self.current_tilt
            + self.commanded_tilt_rate
            * delta_time
        )

        self.current_pan = self._clamp(
            requested_pan,
            self.PAN_MIN_RAD,
            self.PAN_MAX_RAD,
        )
        self.current_tilt = self._clamp(
            requested_tilt,
            self.TILT_MIN_RAD,
            self.TILT_MAX_RAD,
        )

        if delta_time > 0.0:
            self.applied_pan_rate = (
                self.current_pan
                - previous_pan
            ) / delta_time

            self.applied_tilt_rate = (
                self.current_tilt
                - previous_tilt
            ) / delta_time
        else:
            self.applied_pan_rate = 0.0
            self.applied_tilt_rate = 0.0

        pan_message = Float64()
        pan_message.data = self.current_pan

        tilt_message = Float64()
        tilt_message.data = self.current_tilt

        self.pan_publisher.publish(
            pan_message
        )
        self.tilt_publisher.publish(
            tilt_message
        )

        self.ship_pan_publisher.publish(
            pan_message
        )
        self.ship_tilt_publisher.publish(
            tilt_message
        )

        self.update_fire_interlock(now)


def main(args=None) -> None:
    rclpy.init(args=args)

    node = GunRateController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
