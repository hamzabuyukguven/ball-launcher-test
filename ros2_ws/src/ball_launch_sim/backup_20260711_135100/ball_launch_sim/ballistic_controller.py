#!/usr/bin/env python3
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Vector3
from rclpy.node import Node
from std_msgs.msg import Float64, Float64MultiArray


class BallisticController(Node):
    """Predicts a moving target and publishes pan, tilt and launch velocity."""

    def __init__(self) -> None:
        super().__init__('ballistic_controller')

        self.declare_parameter('muzzle_speed', 18.0)
        self.declare_parameter('gravity', 9.81)
        self.declare_parameter('aim_delay', 1.5)
        self.declare_parameter('pivot_height', 1.05)
        self.declare_parameter('muzzle_length', 0.85)
        self.declare_parameter('muzzle_clearance', 0.03)
        self.declare_parameter('target_height', -1.0)
        self.declare_parameter('minimum_range', 1.0)

        self.muzzle_speed = float(self.get_parameter('muzzle_speed').value)
        self.gravity = float(self.get_parameter('gravity').value)
        self.aim_delay = float(self.get_parameter('aim_delay').value)
        self.pivot_height = float(self.get_parameter('pivot_height').value)
        self.muzzle_length = float(self.get_parameter('muzzle_length').value)
        self.muzzle_clearance = float(self.get_parameter('muzzle_clearance').value)
        self.minimum_range = float(self.get_parameter('minimum_range').value)

        package_share = Path(get_package_share_directory('ball_launch_sim'))
        self.ball_radius = self._read_ball_radius(
            package_share / 'models' / 'ball' / 'model.sdf'
        )
        configured_target_height = float(self.get_parameter('target_height').value)
        self.target_height = (
            self.ball_radius if configured_target_height < 0.0 else configured_target_height
        )
        self.launch_distance = (
            self.muzzle_length + self.ball_radius + self.muzzle_clearance
        )

        self.pan_pub = self.create_publisher(Float64, '/pan_cmd', 10)
        self.tilt_pub = self.create_publisher(Float64, '/tilt_cmd', 10)
        self.launch_pub = self.create_publisher(Vector3, '/launch_velocity', 10)
        self.target_sub = self.create_subscription(
            Float64MultiArray,
            '/moving_target_state',
            self.target_callback,
            10,
        )

        self.fire_timer = None
        self.pending_velocity: Optional[Vector3] = None

        self.get_logger().info(
            'Hazır. /moving_target_state verisi [x, y, vx, vy] olarak bekleniyor. '
            f'Gerçek top çıkış uzaklığı={self.launch_distance:.3f} m'
        )

    def _read_ball_radius(self, sdf_path: Path) -> float:
        try:
            root = ET.parse(sdf_path).getroot()
            radius = root.find('.//collision//sphere/radius')
            if radius is None:
                radius = root.find('.//visual//sphere/radius')
            if radius is not None and radius.text:
                value = float(radius.text.strip())
                if value > 0.0:
                    return value
        except (ET.ParseError, OSError, ValueError) as exc:
            self.get_logger().warning(f'Top yarıçapı okunamadı: {exc}')
        return 0.08

    def target_callback(self, msg: Float64MultiArray) -> None:
        if len(msg.data) != 4:
            self.get_logger().error(
                'Hatalı veri: /moving_target_state tam olarak [x, y, vx, vy] içermeli.'
            )
            return

        x, y, target_vx, target_vy = map(float, msg.data)
        solution = self.solve_intercept(x, y, target_vx, target_vy)

        if solution is None:
            self.get_logger().error(
                'Bu hedef mevcut namlu hızıyla vurulamıyor. '
                'Hedef çok yakın, çok uzak veya çok hızlı olabilir.'
            )
            return

        yaw, pitch, ball_vx, ball_vy, ball_vz, flight_time, hit_x, hit_y = solution

        pan_msg = Float64()
        pan_msg.data = yaw
        tilt_msg = Float64()
        tilt_msg.data = pitch
        self.pan_pub.publish(pan_msg)
        self.tilt_pub.publish(tilt_msg)

        launch_msg = Vector3()
        launch_msg.x = ball_vx
        launch_msg.y = ball_vy
        launch_msg.z = ball_vz
        self.pending_velocity = launch_msg

        if self.fire_timer is not None:
            self.fire_timer.cancel()
        self.fire_timer = self.create_timer(self.aim_delay, self.fire_once)

        self.get_logger().info(
            'Komut alındı | hedef=(%.2f, %.2f) m | hedef hızı=(%.2f, %.2f) m/s | '
            'tahmini vurma noktası=(%.2f, %.2f) m | pan=%.1f° | tilt=%.1f° | uçuş=%.2f s'
            % (
                x, y, target_vx, target_vy, hit_x, hit_y,
                math.degrees(yaw), math.degrees(pitch), flight_time,
            )
        )

    def fire_once(self) -> None:
        if self.fire_timer is not None:
            self.fire_timer.cancel()
            self.fire_timer = None

        if self.pending_velocity is None:
            return

        self.launch_pub.publish(self.pending_velocity)
        self.get_logger().info(
            'ATEŞ! Top ilk hız vektörü=(%.2f, %.2f, %.2f) m/s'
            % (
                self.pending_velocity.x,
                self.pending_velocity.y,
                self.pending_velocity.z,
            )
        )
        self.pending_velocity = None

    def solve_intercept(
        self,
        x: float,
        y: float,
        target_vx: float,
        target_vy: float,
    ) -> Optional[Tuple[float, float, float, float, float, float, float, float]]:
        speed = self.muzzle_speed
        initial_range = math.hypot(x, y)
        if initial_range < self.minimum_range:
            return None

        flight_time = max(0.05, initial_range / speed)
        pitch = 0.0
        predicted_x = x
        predicted_y = y

        for _ in range(12):
            predicted_x = x + target_vx * (self.aim_delay + flight_time)
            predicted_y = y + target_vy * (self.aim_delay + flight_time)
            horizontal_range = math.hypot(predicted_x, predicted_y)

            if horizontal_range < self.minimum_range:
                return None

            pitch_solution = self.find_low_arc_pitch(horizontal_range)
            if pitch_solution is None:
                return None
            pitch = pitch_solution

            remaining_range = horizontal_range - self.launch_distance * math.cos(pitch)
            if remaining_range <= 0.0:
                return None

            new_flight_time = remaining_range / (speed * math.cos(pitch))
            if abs(new_flight_time - flight_time) < 1e-4:
                flight_time = new_flight_time
                break
            flight_time = new_flight_time

        yaw = math.atan2(predicted_y, predicted_x)
        horizontal_speed = speed * math.cos(pitch)
        ball_vx = horizontal_speed * math.cos(yaw)
        ball_vy = horizontal_speed * math.sin(yaw)
        ball_vz = speed * math.sin(pitch)

        return (
            yaw, pitch, ball_vx, ball_vy, ball_vz,
            flight_time, predicted_x, predicted_y,
        )

    def find_low_arc_pitch(self, horizontal_range: float) -> Optional[float]:
        lower = math.radians(-5.0)
        upper = math.radians(75.0)
        sample_count = 640

        previous_angle = lower
        previous_value = self.height_error(previous_angle, horizontal_range)

        for index in range(1, sample_count + 1):
            angle = lower + (upper - lower) * index / sample_count
            value = self.height_error(angle, horizontal_range)

            if previous_value == 0.0:
                return previous_angle
            if previous_value * value < 0.0:
                left = previous_angle
                right = angle
                left_value = previous_value

                for _ in range(45):
                    middle = 0.5 * (left + right)
                    middle_value = self.height_error(middle, horizontal_range)
                    if left_value * middle_value <= 0.0:
                        right = middle
                    else:
                        left = middle
                        left_value = middle_value
                return 0.5 * (left + right)

            previous_angle = angle
            previous_value = value

        return None

    def height_error(self, pitch: float, horizontal_range: float) -> float:
        speed = self.muzzle_speed
        horizontal_speed = speed * math.cos(pitch)
        if horizontal_speed <= 1e-6:
            return float('-inf')

        muzzle_horizontal = self.launch_distance * math.cos(pitch)
        muzzle_z = self.pivot_height + self.launch_distance * math.sin(pitch)
        remaining_range = horizontal_range - muzzle_horizontal
        if remaining_range <= 0.0:
            return muzzle_z - self.target_height

        time_to_target = remaining_range / horizontal_speed
        ball_z = (
            muzzle_z
            + speed * math.sin(pitch) * time_to_target
            - 0.5 * self.gravity * time_to_target * time_to_target
        )
        return ball_z - self.target_height


def main(args=None) -> None:
    rclpy.init(args=args)
    node = BallisticController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
