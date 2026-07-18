#!/usr/bin/env python3

import time

import rclpy
from geometry_msgs.msg import Vector3
from rclpy.node import Node
from std_msgs.msg import Bool


class FireCommandAdapter(Node):

    def __init__(self) -> None:
        super().__init__('fire_command_adapter')

        self.declare_parameter('muzzle_speed_mps', 18.0)
        self.declare_parameter('minimum_fire_interval_sec', 0.25)

        self.muzzle_speed = float(
            self.get_parameter('muzzle_speed_mps').value
        )

        self.minimum_fire_interval = float(
            self.get_parameter(
                'minimum_fire_interval_sec'
            ).value
        )

        self.last_fire_time = 0.0

        self.launch_velocity_publisher = self.create_publisher(
            Vector3,
            '/launch_velocity',
            10,
        )

        self.fire_subscription = self.create_subscription(
            Bool,
            '/simulation/fire_request',
            self.fire_request_callback,
            10,
        )

        self.get_logger().info(
            'Fire command adapter started.'
        )
        self.get_logger().info(
            'Input topic: /simulation/fire_request'
        )
        self.get_logger().info(
            'Output topic: /launch_velocity'
        )
        self.get_logger().info(
            f'Muzzle speed: {self.muzzle_speed:.2f} m/s'
        )

    def fire_request_callback(self, message: Bool) -> None:
        if not message.data:
            return

        current_time = time.monotonic()

        if (
            current_time - self.last_fire_time
            < self.minimum_fire_interval
        ):
            self.get_logger().warning(
                'Fire request ignored because of fire-rate limit.'
            )
            return

        if self.muzzle_speed <= 0.0:
            self.get_logger().error(
                'Fire request rejected: muzzle speed must be positive.'
            )
            return

        launch_velocity = Vector3()

        launch_velocity.x = self.muzzle_speed
        launch_velocity.y = 0.0
        launch_velocity.z = 0.0

        self.launch_velocity_publisher.publish(
            launch_velocity
        )

        self.last_fire_time = current_time

        self.get_logger().info(
            f'Projectile launch command published: '
            f'{self.muzzle_speed:.2f} m/s'
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
