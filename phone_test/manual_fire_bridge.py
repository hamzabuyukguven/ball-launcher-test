#!/usr/bin/env python3

import rclpy
from geometry_msgs.msg import Vector3
from naval_interfaces.msg import FireCommand
from rclpy.node import Node


class ManualFireBridge(Node):

    def __init__(self):
        super().__init__("manual_fire_bridge")

        self.launch_publisher = self.create_publisher(
            Vector3,
            "/launch_velocity",
            10,
        )

        self.fire_subscription = self.create_subscription(
            FireCommand,
            "/backend/fire_command",
            self.fire_callback,
            10,
        )

        self.get_logger().info(
            "READY: /backend/fire_command -> /launch_velocity"
        )

    def fire_callback(self, message):
        speed = 60.0

        for field_name in (
            "muzzle_velocity",
            "muzzle_velocity_mps",
            "muzzle_speed_mps",
        ):
            if hasattr(message, field_name):
                speed = float(getattr(message, field_name))
                break

        if speed <= 0.0:
            self.get_logger().warning(
                f"Atış reddedildi, geçersiz hız: {speed}"
            )
            return

        velocity = Vector3()
        velocity.x = speed
        velocity.y = 0.0
        velocity.z = 0.0

        self.launch_publisher.publish(velocity)

        self.get_logger().info(
            f"ATIS AKTARILDI: {speed:.2f} m/s"
        )


def main():
    rclpy.init()
    node = ManualFireBridge()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
