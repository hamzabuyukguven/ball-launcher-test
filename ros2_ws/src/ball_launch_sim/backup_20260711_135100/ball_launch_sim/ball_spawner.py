#!/usr/bin/env python3
import math
import os
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Vector3
from rclpy.node import Node


class BallSpawner(Node):
    """Creates a projectile just outside the muzzle and applies a one-step impulse."""

    def __init__(self) -> None:
        super().__init__('ball_spawner')

        self.declare_parameter('world_name', 'launcher_world')
        self.declare_parameter('ball_mass', 0.15)
        self.declare_parameter('simulation_step', 0.001)
        self.declare_parameter('pivot_height', 1.05)
        self.declare_parameter('muzzle_length', 0.85)
        self.declare_parameter('muzzle_clearance', 0.03)
        self.declare_parameter('entity_settle_time', 0.01)

        self.world_name = str(self.get_parameter('world_name').value)
        self.ball_mass = float(self.get_parameter('ball_mass').value)
        self.simulation_step = float(self.get_parameter('simulation_step').value)
        self.pivot_height = float(self.get_parameter('pivot_height').value)
        self.muzzle_length = float(self.get_parameter('muzzle_length').value)
        self.muzzle_clearance = float(self.get_parameter('muzzle_clearance').value)
        self.entity_settle_time = float(self.get_parameter('entity_settle_time').value)

        package_share = Path(get_package_share_directory('ball_launch_sim'))
        self.ball_sdf = package_share / 'models' / 'ball' / 'model.sdf'
        self.ball_radius = self._read_ball_radius(self.ball_sdf)
        self.shot_counter = 0
        self.busy = False

        self.subscription = self.create_subscription(
            Vector3,
            '/launch_velocity',
            self.velocity_callback,
            10,
        )
        self.get_logger().info(
            'Hazır. Top namlu dışında oluşturulacak ve beklemeden fırlatılacak. '
            f'Top yarıçapı={self.ball_radius:.3f} m'
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

    def velocity_callback(self, msg: Vector3) -> None:
        if self.busy:
            self.get_logger().warning('Önceki top hazırlanıyor; bu ateş komutu atlandı.')
            return

        speed = math.sqrt(msg.x * msg.x + msg.y * msg.y + msg.z * msg.z)
        if speed < 0.1:
            self.get_logger().error('Geçersiz top hız vektörü.')
            return

        self.busy = True
        threading.Thread(
            target=self.spawn_and_launch,
            args=(float(msg.x), float(msg.y), float(msg.z)),
            daemon=True,
        ).start()

    def spawn_and_launch(self, vx: float, vy: float, vz: float) -> None:
        try:
            self.shot_counter += 1
            ball_name = f'ball_{self.shot_counter}_{int(time.time() * 1000)}'

            horizontal_speed = math.hypot(vx, vy)
            yaw = math.atan2(vy, vx)
            pitch = math.atan2(vz, horizontal_speed)

            direction_x = math.cos(pitch) * math.cos(yaw)
            direction_y = math.cos(pitch) * math.sin(yaw)
            direction_z = math.sin(pitch)

            # Ball centre is placed beyond the barrel end, not inside the barrel.
            spawn_distance = self.muzzle_length + self.ball_radius + self.muzzle_clearance
            spawn_x = spawn_distance * direction_x
            spawn_y = spawn_distance * direction_y
            spawn_z = self.pivot_height + spawn_distance * direction_z

            create_command = [
                'ros2', 'run', 'ros_gz_sim', 'create',
                '-world', self.world_name,
                '-file', os.fspath(self.ball_sdf),
                '-name', ball_name,
                '-x', f'{spawn_x:.8f}',
                '-y', f'{spawn_y:.8f}',
                '-z', f'{spawn_z:.8f}',
            ]

            create_result = subprocess.run(
                create_command,
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
            if create_result.returncode != 0:
                self.get_logger().error(
                    'Top oluşturulamadı:\n%s'
                    % (create_result.stderr or create_result.stdout)
                )
                return

            # The old 1-second visibility wait made the ball fall before launch.
            # Creation service has already returned successfully; only a tiny
            # synchronization allowance is needed.
            if self.entity_settle_time > 0.0:
                time.sleep(self.entity_settle_time)

            # /wrench applies the force for exactly one physics step. F=m*dv/dt.
            force_scale = self.ball_mass / self.simulation_step
            force_x = force_scale * vx
            force_y = force_scale * vy
            force_z = force_scale * vz

            payload = (
                f'entity: {{name: "{ball_name}", type: MODEL}}, '
                f'wrench: {{force: {{x: {force_x:.10f}, y: {force_y:.10f}, z: {force_z:.10f}}}, '
                'torque: {x: 0.0, y: 0.0, z: 0.0}}'
            )
            wrench_command = [
                'gz', 'topic',
                '-t', f'/world/{self.world_name}/wrench',
                '-m', 'gz.msgs.EntityWrench',
                '-p', payload,
            ]

            wrench_result = subprocess.run(
                wrench_command,
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
            if wrench_result.returncode != 0:
                self.get_logger().error(
                    'Fırlatma kuvveti uygulanamadı:\n%s'
                    % (wrench_result.stderr or wrench_result.stdout)
                )
                return

            self.get_logger().info(
                '%s oluşturuldu ve anında fırlatıldı | konum=(%.2f, %.2f, %.2f) m '
                '| hız=(%.2f, %.2f, %.2f) m/s'
                % (ball_name, spawn_x, spawn_y, spawn_z, vx, vy, vz)
            )
        except subprocess.TimeoutExpired as exc:
            self.get_logger().error(f'Gazebo komutu zaman aşımına uğradı: {exc}')
        except Exception as exc:  # pragma: no cover
            self.get_logger().error(f'Beklenmeyen fırlatma hatası: {exc}')
        finally:
            self.busy = False


def main(args=None) -> None:
    rclpy.init(args=args)
    node = BallSpawner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
