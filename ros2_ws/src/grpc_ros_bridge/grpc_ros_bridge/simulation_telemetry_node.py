#!/usr/bin/env python3

import math
import time
from typing import Optional

import rclpy
from geometry_msgs.msg import PoseArray
from tf2_msgs.msg import TFMessage
from naval_interfaces.msg import (
    FireCommand,
    GunInfo,
    GunRateCommand,
    GunStatusInfo,
    Heartbeat,
    PlatformPositionInfo,
    PlatformStatusInfo,
    PlatformVelocityInfo,
    StabilizationData,
    TargetPositionInfo,
)
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool


class SimulationTelemetryNode(Node):
    """
    Heybeliada top ve platform telemetry bilgilerini üretir.

    Platform konumu ve yönelimi Gazebo pose bridge üzerinden
    gerçek zamanlı alınır. Parametre değerleri başlangıç/yedek
    değerleri olarak kullanılır.

    Girişler:
      /joint_states
      /simulation/platform_pose
      /simulation/target_pose
      /backend/gun_rate_command
      /simulation/fire_authorized
      /simulation/ready_to_fire

    Çıkışlar:
      /simulation/target_position
      /simulation/gun_info
      /simulation/gun_status
      /simulation/platform_position
      /simulation/platform_velocity
      /simulation/stabilization_data
      /simulation/platform_status
      /simulation/heartbeat
    """

    def __init__(self) -> None:
        super().__init__('simulation_telemetry_node')

        self.declare_parameter(
            'platform_id',
            'heybeliada_ship',
        )

        self.declare_parameter(
            'platform_model_name',
            'heybeliada_ship_float_test',
        )

        self.declare_parameter(
            'target_id',
            'wam_v_target',
        )

        self.declare_parameter(
            'target_model_match',
            'wamv',
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

        self.platform_model_name = str(
            self.get_parameter(
                'platform_model_name'
            ).value
        )

        self.target_id = str(
            self.get_parameter(
                'target_id'
            ).value
        )

        self.target_model_match = str(
            self.get_parameter(
                'target_model_match'
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

        self.platform_roll = 0.0
        self.platform_pitch = 0.0

        self.platform_velocity_x = 0.0
        self.platform_velocity_y = 0.0
        self.platform_velocity_z = 0.0

        self.platform_roll_rate = 0.0
        self.platform_pitch_rate = 0.0
        self.platform_yaw_rate = 0.0

        self.last_platform_pose_time: Optional[float] = None

        self.target_x = 0.0
        self.target_y = 0.0
        self.target_z = 0.0
        self.last_target_pose_time: Optional[float] = None
        self.resolved_target_frame: Optional[str] = None

        self.start_monotonic = time.monotonic()

        self.pan_angle = 0.0
        self.tilt_angle = 0.0

        self.pan_rate = 0.0
        self.tilt_rate = 0.0

        self.control_enabled = False

        self.last_joint_time: Optional[float] = None

        self.firing_until = 0.0
        self.ready_to_fire = False
        self.target_sequence = 0
        self.gun_sequence = 0
        self.gun_status_sequence = 0
        self.platform_position_sequence = 0
        self.platform_velocity_sequence = 0
        self.stabilization_sequence = 0
        self.platform_status_sequence = 0
        self.heartbeat_sequence = 0

        self.target_position_publisher = self.create_publisher(
            TargetPositionInfo,
            '/simulation/target_position',
            10,
        )

        self.gun_publisher = self.create_publisher(
            GunInfo,
            '/simulation/gun_info',
            10,
        )

        self.gun_status_publisher = self.create_publisher(
            GunStatusInfo,
            '/simulation/gun_status',
            10,
        )

        self.platform_position_publisher = self.create_publisher(
            PlatformPositionInfo,
            '/simulation/platform_position',
            10,
        )

        self.platform_velocity_publisher = self.create_publisher(
            PlatformVelocityInfo,
            '/simulation/platform_velocity',
            10,
        )

        self.stabilization_publisher = self.create_publisher(
            StabilizationData,
            '/simulation/stabilization_data',
            10,
        )

        self.platform_status_publisher = self.create_publisher(
            PlatformStatusInfo,
            '/simulation/platform_status',
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
            TFMessage,
            '/simulation/platform_pose',
            self.platform_pose_callback,
            10,
        )

        self.create_subscription(
            PoseArray,
            '/simulation/target_pose',
            self.target_pose_callback,
            10,
        )

        self.create_subscription(
            GunRateCommand,
            '/backend/gun_rate_command',
            self.gun_command_callback,
            10,
        )

        self.create_subscription(
            FireCommand,
            '/simulation/fire_authorized',
            self.fire_authorized_callback,
            10,
        )

        self.create_subscription(
            Bool,
            '/simulation/ready_to_fire',
            self.ready_to_fire_callback,
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
            'Initial platform pose: '
            f'x={self.platform_x:.2f}, '
            f'y={self.platform_y:.2f}, '
            f'z={self.platform_z:.2f}, '
            f'yaw={self.platform_yaw:.2f}'
        )

        self.get_logger().info(
            'Dynamic platform pose input: '
            '/simulation/platform_pose'
        )

        self.get_logger().info(
            'Target position: /simulation/target_position '
            '(dedicated WAM-V PoseArray input)'
        )

        self.get_logger().info(
            'Gun measurements: /simulation/gun_info'
        )

        self.get_logger().info(
            'Gun status: /simulation/gun_status'
        )

        self.get_logger().info(
            'Platform position: /simulation/platform_position'
        )

        self.get_logger().info(
            'Platform velocity: /simulation/platform_velocity'
        )

        self.get_logger().info(
            'Stabilization: /simulation/stabilization_data'
        )

        self.get_logger().info(
            'Platform status: /simulation/platform_status'
        )

        self.get_logger().info(
            'Heartbeat: /simulation/heartbeat'
        )

    @staticmethod
    def _wrap_angle(angle: float) -> float:
        return math.atan2(
            math.sin(angle),
            math.cos(angle),
        )

    @staticmethod
    def _quaternion_to_euler(
        x: float,
        y: float,
        z: float,
        w: float,
    ):
        sin_roll = 2.0 * (w * x + y * z)
        cos_roll = 1.0 - 2.0 * (x * x + y * y)
        roll = math.atan2(sin_roll, cos_roll)

        sin_pitch = 2.0 * (w * y - z * x)

        if abs(sin_pitch) >= 1.0:
            pitch = math.copysign(
                math.pi / 2.0,
                sin_pitch,
            )
        else:
            pitch = math.asin(sin_pitch)

        sin_yaw = 2.0 * (w * z + x * y)
        cos_yaw = 1.0 - 2.0 * (y * y + z * z)
        yaw = math.atan2(sin_yaw, cos_yaw)

        return roll, pitch, yaw

    @staticmethod
    def _normalize_model_name(value: str) -> str:
        return ''.join(
            character.lower()
            for character in value
            if character.isalnum()
        )

    def target_pose_callback(
        self,
        message: PoseArray,
    ) -> None:
        if not message.poses:
            return

        selected_pose = message.poses[0]
        position = selected_pose.position

        values = [
            position.x,
            position.y,
            position.z,
        ]

        if not all(
            math.isfinite(float(value))
            for value in values
        ):
            self.get_logger().warning(
                'Invalid WAM-V target pose ignored.'
            )
            return

        self.target_x = float(position.x)
        self.target_y = float(position.y)
        self.target_z = float(position.z)
        self.last_target_pose_time = time.monotonic()

        if self.resolved_target_frame != 'wam_v':
            self.resolved_target_frame = 'wam_v'
            self.get_logger().info(
                'WAM-V target pose resolved from '
                '/simulation/target_pose'
            )

    def target_pose_is_alive(
        self,
        now_monotonic: float,
    ) -> bool:
        return (
            self.last_target_pose_time is not None
            and (
                now_monotonic
                - self.last_target_pose_time
            ) < 1.0
        )

    def platform_pose_callback(
        self,
        message: TFMessage,
    ) -> None:
        selected_transform = None

        for transform in message.transforms:
            child_frame = str(
                transform.child_frame_id
            )

            if child_frame == self.platform_model_name:
                selected_transform = transform
                break

            if child_frame.endswith(
                f'::{self.platform_model_name}'
            ):
                selected_transform = transform
                break

        if selected_transform is None:
            return

        translation = (
            selected_transform.transform.translation
        )

        orientation = (
            selected_transform.transform.rotation
        )

        values = [
            translation.x,
            translation.y,
            translation.z,
            orientation.x,
            orientation.y,
            orientation.z,
            orientation.w,
        ]

        if not all(
            math.isfinite(float(value))
            for value in values
        ):
            self.get_logger().warning(
                'Invalid platform transform ignored.'
            )
            return

        now = time.monotonic()

        new_x = float(translation.x)
        new_y = float(translation.y)
        new_z = float(translation.z)

        new_roll, new_pitch, new_yaw = (
            self._quaternion_to_euler(
                float(orientation.x),
                float(orientation.y),
                float(orientation.z),
                float(orientation.w),
            )
        )

        if self.last_platform_pose_time is not None:
            delta_time = (
                now - self.last_platform_pose_time
            )

            if delta_time > 1e-6:
                self.platform_velocity_x = (
                    new_x - self.platform_x
                ) / delta_time

                self.platform_velocity_y = (
                    new_y - self.platform_y
                ) / delta_time

                self.platform_velocity_z = (
                    new_z - self.platform_z
                ) / delta_time

                self.platform_roll_rate = (
                    self._wrap_angle(
                        new_roll - self.platform_roll
                    )
                    / delta_time
                )

                self.platform_pitch_rate = (
                    self._wrap_angle(
                        new_pitch - self.platform_pitch
                    )
                    / delta_time
                )

                self.platform_yaw_rate = (
                    self._wrap_angle(
                        new_yaw - self.platform_yaw
                    )
                    / delta_time
                )

        self.platform_x = new_x
        self.platform_y = new_y
        self.platform_z = new_z

        self.platform_roll = new_roll
        self.platform_pitch = new_pitch
        self.platform_yaw = new_yaw

        self.last_platform_pose_time = now

    def platform_pose_is_alive(
        self,
        now_monotonic: float,
    ) -> bool:
        return (
            self.last_platform_pose_time is not None
            and (
                now_monotonic
                - self.last_platform_pose_time
            ) < 1.0
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
        self.control_enabled = bool(
            message.control_enabled
        )

    def fire_authorized_callback(
        self,
        message: FireCommand,
    ) -> None:
        self.firing_until = time.monotonic() + 0.25

    def ready_to_fire_callback(
        self,
        message: Bool,
    ) -> None:
        self.ready_to_fire = bool(message.data)

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
        joint_alive = self.joint_state_is_alive(now_monotonic)
        platform_alive = self.platform_pose_is_alive(now_monotonic)
        now_message = self.get_clock().now().to_msg()

        if self.last_target_pose_time is not None:
            self.target_sequence += 1
            target_message = TargetPositionInfo()
            target_message.sequence = self.target_sequence
            target_message.target_id = self.target_id
            target_message.position_x = self.target_x
            target_message.position_y = self.target_y
            target_message.position_z = self.target_z
            target_message.timestamp = now_message
            self.target_position_publisher.publish(target_message)

        self.gun_sequence += 1
        gun_message = GunInfo()
        gun_message.sequence = self.gun_sequence
        gun_message.gun_id = 'heybeliada_main_gun'
        gun_message.pan_angle = self.pan_angle
        gun_message.tilt_angle = self.tilt_angle
        gun_message.pan_rate = self.pan_rate
        gun_message.tilt_rate = self.tilt_rate
        gun_message.timestamp = now_message
        self.gun_publisher.publish(gun_message)

        self.gun_status_sequence += 1
        gun_status_message = GunStatusInfo()
        gun_status_message.sequence = self.gun_status_sequence
        gun_status_message.gun_id = 'heybeliada_main_gun'
        gun_status_message.control_enabled = self.control_enabled
        gun_status_message.ready_to_fire = self.ready_to_fire
        gun_status_message.firing = now_monotonic < self.firing_until
        gun_status_message.fault = not joint_alive
        gun_status_message.fault_text = (
            '' if joint_alive
            else 'Gazebo joint state is not available.'
        )
        gun_status_message.timestamp = now_message
        self.gun_status_publisher.publish(gun_status_message)

        self.platform_position_sequence += 1
        position_message = PlatformPositionInfo()
        position_message.sequence = self.platform_position_sequence
        position_message.platform_id = self.platform_id
        position_message.position_x = self.platform_x
        position_message.position_y = self.platform_y
        position_message.position_z = self.platform_z
        position_message.timestamp = now_message
        self.platform_position_publisher.publish(position_message)

        self.platform_velocity_sequence += 1
        velocity_message = PlatformVelocityInfo()
        velocity_message.sequence = self.platform_velocity_sequence
        velocity_message.platform_id = self.platform_id
        velocity_message.velocity_x = self.platform_velocity_x
        velocity_message.velocity_y = self.platform_velocity_y
        velocity_message.velocity_z = self.platform_velocity_z
        velocity_message.timestamp = now_message
        self.platform_velocity_publisher.publish(velocity_message)

        self.stabilization_sequence += 1
        stabilization_message = StabilizationData()
        stabilization_message.sequence = self.stabilization_sequence
        stabilization_message.platform_id = self.platform_id
        stabilization_message.roll = self.platform_roll
        stabilization_message.pitch = self.platform_pitch
        stabilization_message.yaw = self.platform_yaw
        stabilization_message.roll_rate = self.platform_roll_rate
        stabilization_message.pitch_rate = self.platform_pitch_rate
        stabilization_message.yaw_rate = self.platform_yaw_rate
        stabilization_message.timestamp = now_message
        self.stabilization_publisher.publish(stabilization_message)

        self.platform_status_sequence += 1
        status_message = PlatformStatusInfo()
        status_message.sequence = self.platform_status_sequence
        status_message.platform_id = self.platform_id
        status_message.simulation_ready = joint_alive and platform_alive

        if joint_alive and platform_alive:
            status_message.mode = 'READY'
        elif not platform_alive:
            status_message.mode = 'WAITING_FOR_PLATFORM_POSE'
        else:
            status_message.mode = 'WAITING_FOR_JOINT_STATE'

        status_message.timestamp = now_message
        self.platform_status_publisher.publish(status_message)

    def publish_heartbeat(self) -> None:
        self.heartbeat_sequence += 1
        now_monotonic = time.monotonic()
        joint_alive = self.joint_state_is_alive(now_monotonic)
        platform_alive = self.platform_pose_is_alive(now_monotonic)

        heartbeat = Heartbeat()
        heartbeat.sequence = self.heartbeat_sequence
        heartbeat.component = 'simulation'
        heartbeat.healthy = joint_alive and platform_alive

        if joint_alive and platform_alive:
            heartbeat.state = 'RUNNING'
        elif not platform_alive:
            heartbeat.state = 'WAITING_FOR_PLATFORM_POSE'
        else:
            heartbeat.state = 'WAITING_FOR_JOINT_STATE'

        heartbeat.uptime = now_monotonic - self.start_monotonic
        heartbeat.timestamp = self.get_clock().now().to_msg()
        self.heartbeat_publisher.publish(heartbeat)


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
