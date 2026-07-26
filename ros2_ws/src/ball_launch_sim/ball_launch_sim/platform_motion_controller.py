#!/usr/bin/env python3

import math
import subprocess
import threading
import time
from typing import Tuple

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class PlatformMotionController(Node):

    def __init__(self) -> None:
        super().__init__("platform_motion_controller")

        self.declare_parameter(
            "model_name",
            "heybeliada_ship_float_test",
        )
        self.declare_parameter(
            "max_forward_speed_mps",
            2.0,
        )
        self.declare_parameter(
            "max_lateral_speed_mps",
            1.0,
        )
        self.declare_parameter(
            "max_yaw_rate_rad_s",
            0.20,
        )
        self.declare_parameter(
            "command_timeout_sec",
            0.60,
        )

        self.model_name = str(
            self.get_parameter("model_name").value
        )
        self.max_forward_speed = float(
            self.get_parameter(
                "max_forward_speed_mps"
            ).value
        )
        self.max_lateral_speed = float(
            self.get_parameter(
                "max_lateral_speed_mps"
            ).value
        )
        self.max_yaw_rate = float(
            self.get_parameter(
                "max_yaw_rate_rad_s"
            ).value
        )
        self.command_timeout = float(
            self.get_parameter(
                "command_timeout_sec"
            ).value
        )

        self.gz_topic = (
            f"/model/{self.model_name}/cmd_vel"
        )

        self.command_lock = threading.Lock()

        self.last_receive_time = 0.0
        self.last_command: Tuple[float, float, float] = (
            0.0,
            0.0,
            0.0,
        )
        self.platform_moving = False

        self.create_subscription(
            Twist,
            "/backend/platform_cmd_vel",
            self.command_callback,
            10,
        )

        self.create_timer(
            0.10,
            self.watchdog_callback,
        )

        self.get_logger().info(
            "Platform velocity controller ready."
        )
        self.get_logger().info(
            f"Gazebo topic: {self.gz_topic}"
        )
        self.get_logger().info(
            "ROS topic: /backend/platform_cmd_vel"
        )

    @staticmethod
    def clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        return max(
            minimum,
            min(maximum, value),
        )

    def publish_gazebo_velocity(
        self,
        forward_speed: float,
        lateral_speed: float,
        yaw_rate: float,
    ) -> None:
        payload = (
            "linear: {"
            f" x: {forward_speed:.6f}"
            f" y: {lateral_speed:.6f}"
            " z: 0.0"
            " } "
            "angular: {"
            " x: 0.0"
            " y: 0.0"
            f" z: {yaw_rate:.6f}"
            " }"
        )

        result = subprocess.run(
            [
                "gz",
                "topic",
                "-t",
                self.gz_topic,
                "-m",
                "gz.msgs.Twist",
                "-p",
                payload,
            ],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )

        if result.returncode != 0:
            error = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Unknown Gazebo topic error."
            )
            raise RuntimeError(error)

    def command_callback(
        self,
        message: Twist,
    ) -> None:
        forward_speed = self.clamp(
            float(message.linear.x),
            -self.max_forward_speed,
            self.max_forward_speed,
        )

        lateral_speed = self.clamp(
            float(message.linear.y),
            -self.max_lateral_speed,
            self.max_lateral_speed,
        )

        yaw_rate = self.clamp(
            float(message.angular.z),
            -self.max_yaw_rate,
            self.max_yaw_rate,
        )

        values = (
            forward_speed,
            lateral_speed,
            yaw_rate,
        )

        if not all(
            math.isfinite(value)
            for value in values
        ):
            self.get_logger().error(
                "Non-finite platform command rejected."
            )
            return

        rounded_command = tuple(
            round(value, 5)
            for value in values
        )

        with self.command_lock:
            self.last_receive_time = time.monotonic()

            # Aynı komut tekrar geldiyse yalnızca
            # watchdog süresini yeniler.
            if rounded_command == self.last_command:
                return

            try:
                self.publish_gazebo_velocity(
                    forward_speed,
                    lateral_speed,
                    yaw_rate,
                )

                self.last_command = rounded_command
                self.platform_moving = any(
                    abs(value) > 0.0001
                    for value in rounded_command
                )

                self.get_logger().info(
                    "Platform command: "
                    f"forward={forward_speed:.2f} m/s, "
                    f"lateral={lateral_speed:.2f} m/s, "
                    f"yaw={yaw_rate:.3f} rad/s"
                )

            except Exception as error:
                self.get_logger().error(
                    f"Velocity command failed: {error}"
                )

    def stop_platform(self) -> None:
        try:
            self.publish_gazebo_velocity(
                0.0,
                0.0,
                0.0,
            )

            self.last_command = (
                0.0,
                0.0,
                0.0,
            )
            self.platform_moving = False

            self.get_logger().info(
                "Platform stopped."
            )

        except Exception as error:
            self.get_logger().error(
                f"Platform stop failed: {error}"
            )

    def watchdog_callback(self) -> None:
        with self.command_lock:
            if not self.platform_moving:
                return

            elapsed = (
                time.monotonic()
                - self.last_receive_time
            )

            if elapsed > self.command_timeout:
                self.get_logger().warning(
                    "Platform command timeout; stopping."
                )
                self.stop_platform()


def main(args=None) -> None:
    rclpy.init(args=args)

    node = PlatformMotionController()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        with node.command_lock:
            node.stop_platform()

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
