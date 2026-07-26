#!/usr/bin/env python3

import math
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import rclpy
from geometry_msgs.msg import Vector3
from rclpy.node import Node


class BallSpawner(Node):

    def __init__(self) -> None:
        super().__init__('ball_spawner')

        self.declare_parameter(
            'world_name',
            'heybeliada_ship_test_world',
        )

        self.declare_parameter(
            'reference_model',
            'heybeliada_ship',
        )

        self.declare_parameter(
            'reference_link',
            'muzzle_link',
        )

        self.declare_parameter(
            'muzzle_clearance',
            0.30,
        )

        self.declare_parameter(
            'ball_radius',
            0.12,
        )

        self.declare_parameter(
            'ball_mass',
            0.15,
        )

        self.world_name = str(
            self.get_parameter('world_name').value
        )

        self.reference_model = str(
            self.get_parameter(
                'reference_model'
            ).value
        )

        self.reference_link = str(
            self.get_parameter(
                'reference_link'
            ).value
        )

        self.muzzle_clearance = float(
            self.get_parameter(
                'muzzle_clearance'
            ).value
        )

        self.ball_radius = float(
            self.get_parameter(
                'ball_radius'
            ).value
        )

        self.ball_mass = float(
            self.get_parameter(
                'ball_mass'
            ).value
        )

        self.generated_directory = (
            Path(tempfile.gettempdir())
            / 'heybeliada_projectiles'
        )

        self.generated_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.shot_counter = 0
        self.busy = False
        self.lock = threading.Lock()

        self.subscription = self.create_subscription(
            Vector3,
            '/launch_velocity',
            self.velocity_callback,
            10,
        )

        self.get_logger().info(
            'Projectile plugin ball spawner started.'
        )
        self.get_logger().info(
            f'World: {self.world_name}'
        )
        self.get_logger().info(
            f'Reference: {self.reference_model}'
            f'::{self.reference_link}'
        )

    def velocity_callback(
        self,
        message: Vector3,
    ) -> None:
        velocity = (
            float(message.x),
            float(message.y),
            float(message.z),
        )

        if not all(math.isfinite(v) for v in velocity):
            self.get_logger().error(
                'Atış reddedildi: geçersiz hız.'
            )
            return

        speed = math.sqrt(
            velocity[0] ** 2
            + velocity[1] ** 2
            + velocity[2] ** 2
        )

        if speed < 0.05:
            self.get_logger().warning(
                'Atış reddedildi: hız çok düşük.'
            )
            return

        with self.lock:
            if self.busy:
                self.get_logger().warning(
                    'Önceki mermi oluşturuluyor.'
                )
                return

            self.busy = True

        worker = threading.Thread(
            target=self.spawn_projectile,
            args=velocity,
            daemon=True,
        )

        worker.start()

    def spawn_projectile(
        self,
        vx: float,
        vy: float,
        vz: float,
    ) -> None:
        try:
            self.shot_counter += 1

            ball_name = (
                f'ball_{self.shot_counter}_'
                f'{int(time.time() * 1000)}'
            )

            inertia = (
                0.4
                * self.ball_mass
                * self.ball_radius
                * self.ball_radius
            )

            sdf_text = f'''<?xml version="1.0"?>
<sdf version="1.9">
  <model
    name="projectile_ball"
    canonical_link="ball_link">

    <pose>0 0 5 0 0 0</pose>

    <static>false</static>
    <self_collide>false</self_collide>

    <link name="ball_link">

      <gravity>false</gravity>

      <velocity_decay>
        <linear>0.0</linear>
        <angular>0.0</angular>
      </velocity_decay>

      <inertial>
        <mass>{self.ball_mass:.9f}</mass>

        <inertia>
          <ixx>{inertia:.12f}</ixx>
          <iyy>{inertia:.12f}</iyy>
          <izz>{inertia:.12f}</izz>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyz>0</iyz>
        </inertia>
      </inertial>


      <visual name="shell_body_visual">
        <!-- Silindir varsayılan olarak Z eksenindedir.
             Y etrafında 90 derece döndürülerek X yönüne alınır. -->
        <pose>0 0 0 0 1.57079632679 0</pose>

        <geometry>
          <cylinder>
            <radius>0.038</radius>
            <length>0.22</length>
          </cylinder>
        </geometry>

        <material>
          <ambient>0.16 0.17 0.15 1</ambient>
          <diffuse>0.30 0.32 0.28 1</diffuse>
          <specular>0.55 0.55 0.50 1</specular>
          <pbr>
            <metal>
              <metalness>0.70</metalness>
              <roughness>0.32</roughness>
            </metal>
          </pbr>
        </material>
      </visual>

      <visual name="shell_nose_visual">
        <!-- Sivri burun -->
        <pose>0.16 0 0 0 1.57079632679 0</pose>

        <geometry>
          <cone>
            <radius>0.038</radius>
            <length>0.10</length>
          </cone>
        </geometry>

        <material>
          <ambient>0.12 0.13 0.12 1</ambient>
          <diffuse>0.24 0.26 0.23 1</diffuse>
          <specular>0.60 0.60 0.55 1</specular>
          <pbr>
            <metal>
              <metalness>0.75</metalness>
              <roughness>0.28</roughness>
            </metal>
          </pbr>
        </material>
      </visual>

      <visual name="shell_band_visual">
        <!-- Bakır tahrik bandı -->
        <pose>-0.085 0 0 0 1.57079632679 0</pose>

        <geometry>
          <cylinder>
            <radius>0.040</radius>
            <length>0.018</length>
          </cylinder>
        </geometry>

        <material>
          <ambient>0.30 0.11 0.025 1</ambient>
          <diffuse>0.68 0.25 0.055 1</diffuse>
          <specular>0.70 0.42 0.18 1</specular>
          <pbr>
            <metal>
              <metalness>0.80</metalness>
              <roughness>0.25</roughness>
            </metal>
          </pbr>
        </material>
      </visual>

    </link>

    <plugin
      filename="projectile_launch_system"
      name="projectile_launch_plugin::ProjectileLaunchSystem">

      <reference_model>
        {self.reference_model}
      </reference_model>

      <reference_link>
        {self.reference_link}
      </reference_link>

      <local_velocity>
        {vx:.9f} {vy:.9f} {vz:.9f}
      </local_velocity>

      <clearance>
        {self.muzzle_clearance:.9f}
      </clearance>

      <gravity_mps2>
        9.81
      </gravity_mps2>

      <ground_z>
        {self.ball_radius:.9f}
      </ground_z>

      <max_flight_time>
        20.0
      </max_flight_time>

    </plugin>

  </model>
</sdf>
'''

            sdf_file = (
                self.generated_directory
                / f'{ball_name}.sdf'
            )

            sdf_file.write_text(sdf_text)

            command = [
                'ros2',
                'run',
                'ros_gz_sim',
                'create',
                '-world',
                self.world_name,
                '-file',
                str(sdf_file),
                '-name',
                ball_name,
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=15.0,
                check=False,
            )

            if result.returncode != 0:
                output = (
                    result.stderr.strip()
                    or result.stdout.strip()
                )

                raise RuntimeError(
                    f'Mermi oluşturulamadı: {output}'
                )

            self.get_logger().info(
                f'{ball_name} oluşturuldu | '
                f'yerel hız=({vx:.2f}, '
                f'{vy:.2f}, {vz:.2f}) m/s'
            )

        except Exception as exc:
            self.get_logger().error(
                f'Atış hatası: {exc}'
            )

        finally:
            with self.lock:
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

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
