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
    """Converts target coordinates and launcher motor RPM values into a shot."""

    def __init__(self) -> None:
        super().__init__('ballistic_controller')

        self.declare_parameter('gravity', 9.81)
        self.declare_parameter('aim_delay', 1.5)
        self.declare_parameter('pivot_height', 1.05)
        self.declare_parameter('muzzle_length', 0.85)
        self.declare_parameter('muzzle_clearance', 0.03)
        self.declare_parameter('target_height', -1.0)
        self.declare_parameter('minimum_range', 1.0)

        # Varsayım: İki karşılıklı fırlatma çarkının yarıçapı 5 cm.
        # Top çıkış hızı = ortalama çark çevresel hızı x verim katsayısı.
        self.declare_parameter('launcher_wheel_radius', 0.05)
        self.declare_parameter('speed_efficiency', 0.75)
        self.declare_parameter('minimum_motor_rpm', 300.0)
        self.declare_parameter('maximum_motor_rpm', 12000.0)

        self.gravity = float(self.get_parameter('gravity').value)
        self.aim_delay = float(self.get_parameter('aim_delay').value)
        self.pivot_height = float(self.get_parameter('pivot_height').value)
        self.muzzle_length = float(self.get_parameter('muzzle_length').value)
        self.muzzle_clearance = float(self.get_parameter('muzzle_clearance').value)
        self.minimum_range = float(self.get_parameter('minimum_range').value)
        self.wheel_radius = float(
            self.get_parameter('launcher_wheel_radius').value
        )
        self.speed_efficiency = float(
            self.get_parameter('speed_efficiency').value
        )
        self.minimum_motor_rpm = float(
            self.get_parameter('minimum_motor_rpm').value
        )
        self.maximum_motor_rpm = float(
            self.get_parameter('maximum_motor_rpm').value
        )

        package_share = Path(get_package_share_directory('ball_launch_sim'))
        self.ball_radius = self._read_ball_radius(
            package_share / 'models' / 'ball' / 'model.sdf'
        )
        self.launch_distance = (
            self.muzzle_length + self.ball_radius + self.muzzle_clearance
        )

        configured_target_height = float(
            self.get_parameter('target_height').value
        )
        self.target_height = (
            self.ball_radius
            if configured_target_height < 0.0
            else configured_target_height
        )

        self.pan_pub = self.create_publisher(Float64, '/pan_cmd', 10)
        self.tilt_pub = self.create_publisher(Float64, '/tilt_cmd', 10)
        self.launch_pub = self.create_publisher(Vector3, '/launch_velocity', 10)
        self.command_sub = self.create_subscription(
            Float64MultiArray,
            '/launcher_command',
            self.command_callback,
            10,
        )

        self.fire_timer = None
        self.pending_velocity: Optional[Vector3] = None

        self.get_logger().info(
            'Hazır. /launcher_command verisi '
            '[x, y, sol_motor_rpm, sag_motor_rpm] olarak bekleniyor.'
        )
        self.get_logger().info(
            'Motor RPM -> top hızı modeli: çark yarıçapı=%.3f m, verim=%.2f'
            % (self.wheel_radius, self.speed_efficiency)
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

    def command_callback(self, msg: Float64MultiArray) -> None:
        if len(msg.data) != 4:
            self.get_logger().error(
                'Hatalı veri: /launcher_command tam olarak '
                '[x, y, sol_motor_rpm, sag_motor_rpm] içermeli.'
            )
            return

        x, y, left_rpm, right_rpm = map(float, msg.data)
        horizontal_range = math.hypot(x, y)

        if horizontal_range < self.minimum_range:
            self.get_logger().error(
                'Hedef çok yakın: yatay mesafe %.2f m, minimum %.2f m.'
                % (horizontal_range, self.minimum_range)
            )
            return

        abs_left_rpm = abs(left_rpm)
        abs_right_rpm = abs(right_rpm)
        for label, rpm in (
            ('Sol motor', abs_left_rpm),
            ('Sağ motor', abs_right_rpm),
        ):
            if rpm < self.minimum_motor_rpm or rpm > self.maximum_motor_rpm:
                self.get_logger().error(
                    '%s RPM değeri geçersiz: %.0f RPM. İzin verilen aralık %.0f-%.0f RPM.'
                    % (
                        label,
                        rpm,
                        self.minimum_motor_rpm,
                        self.maximum_motor_rpm,
                    )
                )
                return

        average_rpm = 0.5 * (abs_left_rpm + abs_right_rpm)
        muzzle_speed = self.rpm_to_ball_speed(average_rpm)

        if average_rpm > 0.0:
            rpm_difference_ratio = abs(abs_left_rpm - abs_right_rpm) / average_rpm
            if rpm_difference_ratio > 0.20:
                self.get_logger().warning(
                    'Motor RPM değerleri arasında büyük fark var. '
                    'Bu sürümde farkın oluşturduğu top dönüşü/spin modellenmiyor; '
                    'yalnızca ortalama RPM top hızında kullanılıyor.'
                )

        solution = self.solve_stationary_target(x, y, muzzle_speed)
        if solution is None:
            self.get_logger().error(
                'Hedef bu motor hızlarıyla vurulamıyor: mesafe=%.2f m, '
                'hesaplanan top çıkış hızı=%.2f m/s. RPM değerlerini artır '
                'veya hedefi yaklaştır.'
                % (horizontal_range, muzzle_speed)
            )
            return

        yaw, pitch, ball_vx, ball_vy, ball_vz, flight_time = solution

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
            'Komut alındı | hedef=(%.2f, %.2f) m | motorlar=(%.0f, %.0f) RPM '
            '| top çıkış hızı=%.2f m/s | pan=%.1f° | tilt=%.1f° | uçuş=%.2f s'
            % (
                x,
                y,
                left_rpm,
                right_rpm,
                muzzle_speed,
                math.degrees(yaw),
                math.degrees(pitch),
                flight_time,
            )
        )

    def rpm_to_ball_speed(self, average_rpm: float) -> float:
        wheel_surface_speed = (
            average_rpm * 2.0 * math.pi * self.wheel_radius / 60.0
        )
        return wheel_surface_speed * self.speed_efficiency

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

    def solve_stationary_target(
        self,
        x: float,
        y: float,
        speed: float,
    ) -> Optional[Tuple[float, float, float, float, float, float]]:
        horizontal_range = math.hypot(x, y)
        if horizontal_range < self.minimum_range or speed <= 0.1:
            return None

        pitch = self.find_low_arc_pitch(horizontal_range, speed)
        if pitch is None:
            return None

        yaw = math.atan2(y, x)
        horizontal_speed = speed * math.cos(pitch)
        remaining_range = (
            horizontal_range - self.launch_distance * math.cos(pitch)
        )
        if horizontal_speed <= 1e-6 or remaining_range <= 0.0:
            return None

        flight_time = remaining_range / horizontal_speed
        ball_vx = horizontal_speed * math.cos(yaw)
        ball_vy = horizontal_speed * math.sin(yaw)
        ball_vz = speed * math.sin(pitch)

        return yaw, pitch, ball_vx, ball_vy, ball_vz, flight_time

    def find_low_arc_pitch(
        self,
        horizontal_range: float,
        speed: float,
    ) -> Optional[float]:
        lower = math.radians(-5.0)
        upper = math.radians(75.0)
        sample_count = 640

        previous_angle = lower
        previous_value = self.height_error(
            previous_angle,
            horizontal_range,
            speed,
        )

        for index in range(1, sample_count + 1):
            angle = lower + (upper - lower) * index / sample_count
            value = self.height_error(angle, horizontal_range, speed)

            if previous_value == 0.0:
                return previous_angle
            if previous_value * value < 0.0:
                left = previous_angle
                right = angle
                left_value = previous_value

                for _ in range(45):
                    middle = 0.5 * (left + right)
                    middle_value = self.height_error(
                        middle,
                        horizontal_range,
                        speed,
                    )
                    if left_value * middle_value <= 0.0:
                        right = middle
                    else:
                        left = middle
                        left_value = middle_value
                return 0.5 * (left + right)

            previous_angle = angle
            previous_value = value

        return None

    def height_error(
        self,
        pitch: float,
        horizontal_range: float,
        speed: float,
    ) -> float:
        horizontal_speed = speed * math.cos(pitch)
        if horizontal_speed <= 1e-6:
            return float('-inf')

        launch_horizontal = self.launch_distance * math.cos(pitch)
        launch_z = self.pivot_height + self.launch_distance * math.sin(pitch)
        remaining_range = horizontal_range - launch_horizontal
        if remaining_range <= 0.0:
            return launch_z - self.target_height

        time_to_target = remaining_range / horizontal_speed
        ball_z = (
            launch_z
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
