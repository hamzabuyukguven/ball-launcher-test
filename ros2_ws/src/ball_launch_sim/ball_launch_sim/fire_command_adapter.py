#!/usr/bin/env python3

import math
import time

import rclpy
from geometry_msgs.msg import Vector3
from naval_interfaces.msg import FireCommand
from rclpy.node import Node


class FireCommandAdapter(Node):
    """Convert an interlock-authorized fire command to launch velocity."""

    def __init__(self) -> None:
        super().__init__('fire_command_adapter')

        self.declare_parameter('muzzle_speed_mps', 18.0)
        self.declare_parameter('minimum_fire_interval_sec', 0.25)

        self.default_muzzle_speed = float(
            self.get_parameter('muzzle_speed_mps').value
        )
        self.minimum_fire_interval = float(
            self.get_parameter('minimum_fire_interval_sec').value
        )
        self.last_fire_time = 0.0

        self.launch_velocity_publisher = self.create_publisher(
            Vector3,
            '/launch_velocity',
            10,
        )
        self.fire_subscription = self.create_subscription(
            FireCommand,
            '/simulation/fire_authorized',
            self.fire_command_callback,
            10,
        )

        self.get_logger().info('Fire command adapter v2 started.')
        self.get_logger().info(
            'Authorized fire input: /simulation/fire_authorized'
        )
        self.get_logger().info('Output: /launch_velocity')

    def fire_command_callback(self, message: FireCommand) -> None:
        muzzle_speed = float(message.muzzle_velocity)

        if not math.isfinite(muzzle_speed) or muzzle_speed <= 0.0:
            self.get_logger().error(
                'Authorized fire rejected: muzzle velocity must be positive.'
            )
            return

        current_time = time.monotonic()
        if (
            current_time - self.last_fire_time
            < self.minimum_fire_interval
        ):
            self.get_logger().warning(
                'Authorized fire ignored because of fire-rate limit.'
            )
            return

        launch_velocity = Vector3()
        launch_velocity.x = muzzle_speed
        launch_velocity.y = 0.0
        launch_velocity.z = 0.0
        self.launch_velocity_publisher.publish(launch_velocity)
        self.last_fire_time = current_time

        self.get_logger().info(
            'Projectile launch command published: '
            f'sequence={message.sequence}, '
            f'muzzle_velocity={muzzle_speed:.2f} m/s'
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FireCommandAdapter()

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
