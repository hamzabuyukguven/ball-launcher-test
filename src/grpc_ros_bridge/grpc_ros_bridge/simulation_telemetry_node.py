#!/usr/bin/env python3

import time
from typing import Optional

import rclpy
from naval_interfaces.msg import (
    GunInfo,
    GunRateCommand,
    Heartbeat,
    PlatformInfo,
)
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool


class SimulationTelemetryNode(Node):
    """
    Heybeliada top ve platform telemetry bilgilerini üretir.

    Şu an gemi boş dünyada sabit durmaktadır. Bu nedenle platform
    konumu ROS parametrelerinden alınır.

    Girişler:
      /joint_states
      /backend/gun_rate_command
      /simulation/fire_request

    Çıkışlar:
      /simulation/gun_info
      /simulation/platform_info
      /simulation/heartbeat
    """

    def __init__(self) -> None:
        super().__init__('simulation_telemetry_node')

        self.declare_parameter(
            'platform_id',
            'heybeliada_ship',
        )

        self.declare_parameter(
            'platform_x_m',
            0.0,
        )

        self.declare_parameter(
            'platform_y_m',
            0.0,
        )

        self.declare_parameter(
            'platform_z_m',
            3.92,
        )

        self.declare_parameter(
            'platform_yaw_rad',
            0.0,
        )

        self.platform_id = str(
            self.get_parameter(
                'platform_id'
            ).value
        )

        self.platform_x = float(
            self.get_parameter(
                'platform_x_m'
            ).value
        )

        self.platform_y = float(
            self.get_parameter(
                'platform_y_m'
            ).value
        )

        self.platform_z = float(
            self.get_parameter(
                'platform_z_m'
            ).value
        )

        self.platform_yaw = float(
            self.get_parameter(
                'platform_yaw_rad'
            ).value
        )

        self.start_monotonic = time.monotonic()

        self.pan_angle = 0.0
        self.tilt_angle = 0.0

        self.pan_rate = 0.0
        self.tilt_rate = 0.0

        self.commanded_pan_rate = 0.0
        self.commanded_tilt_rate = 0.0

        self.control_enabled = False

        self.last_joint_time: Optional[float] = None

        self.firing_until = 0.0
        self.heartbeat_sequence = 0

        self.gun_publisher = self.create_publisher(
            GunInfo,
            '/simulation/gun_info',
            10,
        )

        self.platform_publisher = self.create_publisher(
            PlatformInfo,
            '/simulation/platform_info',
            10,
        )

        self.heartbeat_publisher = self.create_publisher(
            Heartbeat,
            '/simulation/heartbeat',
            10,
        )

        self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10,
        )

        self.create_subscription(
            GunRateCommand,
            '/backend/gun_rate_command',
            self.gun_command_callback,
            10,
        )

        self.create_subscription(
            Bool,
            '/simulation/fire_request',
            self.fire_request_callback,
            10,
        )

        self.create_timer(
            0.1,
            self.publish_simulation_telemetry,
        )

        self.create_timer(
            1.0,
            self.publish_heartbeat,
        )

        self.get_logger().info(
            'Simulation telemetry node started.'
        )

        self.get_logger().info(
            'Fixed platform pose: '
            f'x={self.platform_x:.2f}, '
            f'y={self.platform_y:.2f}, '
            f'z={self.platform_z:.2f}, '
            f'yaw={self.platform_yaw:.2f}'
        )

        self.get_logger().info(
            'Gun telemetry: /simulation/gun_info'
        )

        self.get_logger().info(
            'Platform telemetry: /simulation/platform_info'
        )

        self.get_logger().info(
            'Heartbeat: /simulation/heartbeat'
        )

    def joint_state_callback(
        self,
        message: JointState,
    ) -> None:
        indexes = {
            name: index
            for index, name in enumerate(message.name)
        }

        pan_index = indexes.get('pan_joint')
        tilt_index = indexes.get('tilt_joint')

        if (
            pan_index is not None
            and pan_index < len(message.position)
        ):
            self.pan_angle = float(
                message.position[pan_index]
            )

        if (
            tilt_index is not None
            and tilt_index < len(message.position)
        ):
            self.tilt_angle = float(
                message.position[tilt_index]
            )

        if (
            pan_index is not None
            and pan_index < len(message.velocity)
        ):
            self.pan_rate = float(
                message.velocity[pan_index]
            )

        if (
            tilt_index is not None
            and tilt_index < len(message.velocity)
        ):
            self.tilt_rate = float(
                message.velocity[tilt_index]
            )

        self.last_joint_time = time.monotonic()

    def gun_command_callback(
        self,
        message: GunRateCommand,
    ) -> None:
        self.commanded_pan_rate = float(
            message.pan_rate_rad_s
        )

        self.commanded_tilt_rate = float(
            message.tilt_rate_rad_s
        )

        self.control_enabled = bool(
            message.control_enabled
        )

    def fire_request_callback(
        self,
        message: Bool,
    ) -> None:
        if message.data:
            self.firing_until = (
                time.monotonic() + 0.25
            )

    def joint_state_is_alive(
        self,
        now_monotonic: float,
    ) -> bool:
        return (
            self.last_joint_time is not None
            and (
                now_monotonic
                - self.last_joint_time
            ) < 1.0
        )

    def publish_simulation_telemetry(self) -> None:
        now_monotonic = time.monotonic()

        joint_alive = self.joint_state_is_alive(
            now_monotonic
        )

        moving = (
            abs(self.pan_rate) > 0.01
            or abs(self.tilt_rate) > 0.01
            or abs(self.commanded_pan_rate) > 0.001
            or abs(self.commanded_tilt_rate) > 0.001
        )

        now_message = self.get_clock().now().to_msg()

        # --------------------------------------------------
        # TOP TELEMETRY
        # --------------------------------------------------

        gun_message = GunInfo()

        gun_message.header.stamp = now_message
        gun_message.header.frame_id = (
            self.platform_id
        )

        gun_message.gun_id = (
            'heybeliada_main_gun'
        )

        gun_message.pan_angle_rad = (
            self.pan_angle
        )

        gun_message.tilt_angle_rad = (
            self.tilt_angle
        )

        gun_message.pan_rate_rad_s = (
            self.pan_rate
        )

        gun_message.tilt_rate_rad_s = (
            self.tilt_rate
        )

        gun_message.commanded_pan_rate_rad_s = (
            self.commanded_pan_rate
        )

        gun_message.commanded_tilt_rate_rad_s = (
            self.commanded_tilt_rate
        )

        gun_message.control_enabled = (
            self.control_enabled
        )

        gun_message.ready_to_fire = (
            joint_alive
            and self.control_enabled
            and not moving
        )

        gun_message.firing = (
            now_monotonic < self.firing_until
        )

        gun_message.fault = not joint_alive

        if joint_alive:
            gun_message.fault_text = ''
        else:
            gun_message.fault_text = (
                'Gazebo joint state is not available.'
            )

        self.gun_publisher.publish(
            gun_message
        )

        # --------------------------------------------------
        # PLATFORM TELEMETRY
        # --------------------------------------------------

        platform_message = PlatformInfo()

        platform_message.header.stamp = now_message
        platform_message.header.frame_id = 'world'

        platform_message.platform_id = (
            self.platform_id
        )

        platform_message.position_x_m = (
            self.platform_x
        )

        platform_message.position_y_m = (
            self.platform_y
        )

        platform_message.position_z_m = (
            self.platform_z
        )

        platform_message.velocity_x_mps = 0.0
        platform_message.velocity_y_mps = 0.0
        platform_message.velocity_z_mps = 0.0

        platform_message.yaw_rad = (
            self.platform_yaw
        )

        platform_message.yaw_rate_rad_s = 0.0

        platform_message.simulation_ready = (
            joint_alive
        )

        if joint_alive:
            platform_message.mode = 'READY'
        else:
            platform_message.mode = (
                'WAITING_FOR_SIMULATION'
            )

        self.platform_publisher.publish(
            platform_message
        )

    def publish_heartbeat(self) -> None:
        self.heartbeat_sequence += 1

        now_monotonic = time.monotonic()

        joint_alive = self.joint_state_is_alive(
            now_monotonic
        )

        heartbeat = Heartbeat()

        heartbeat.header.stamp = (
            self.get_clock().now().to_msg()
        )

        heartbeat.header.frame_id = (
            self.platform_id
        )

        heartbeat.component = 'simulation'

        heartbeat.sequence = (
            self.heartbeat_sequence
        )

        heartbeat.healthy = joint_alive

        if joint_alive:
            heartbeat.state = 'RUNNING'
        else:
            heartbeat.state = (
                'WAITING_FOR_JOINT_STATE'
            )

        heartbeat.uptime_sec = (
            now_monotonic
            - self.start_monotonic
        )

        self.heartbeat_publisher.publish(
            heartbeat
        )


def main(args=None) -> None:
    rclpy.init(args=args)

    node = SimulationTelemetryNode()

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
