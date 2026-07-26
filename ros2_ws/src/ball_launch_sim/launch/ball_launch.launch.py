#!/usr/bin/env python3
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    package_share = get_package_share_directory('ball_launch_sim')
    ros_gz_share = get_package_share_directory('ros_gz_sim')

    world_path = os.path.join(package_share, 'worlds', 'launcher_world.sdf')
    model_path = os.path.join(package_share, 'models')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items(),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/pan_cmd@std_msgs/msg/Float64@gz.msgs.Double',
            '/tilt_cmd@std_msgs/msg/Float64@gz.msgs.Double',
        ],
        output='screen',
    )

    common_geometry = {
        'pivot_height': 1.05,
        'muzzle_length': 0.85,
        'muzzle_clearance': 0.03,
    }

    controller = Node(
        package='ball_launch_sim',
        executable='ballistic_controller',
        output='screen',
        parameters=[{
            'muzzle_speed': 18.0,
            'aim_delay': 1.5,
            'target_height': -1.0,
            **common_geometry,
        }],
    )

    spawner = Node(
        package='ball_launch_sim',
        executable='ball_spawner',
        output='screen',
        parameters=[{
            'world_name': 'launcher_world',
            'ball_mass': 0.15,
            'simulation_step': 0.001,
            'entity_settle_time': 0.01,
            **common_geometry,
        }],
    )

    return LaunchDescription([
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', model_path),
        gazebo,
        bridge,
        controller,
        spawner,
    ])
