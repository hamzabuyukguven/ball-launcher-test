#!/usr/bin/env python3

import os
from pathlib import Path

from ament_index_python.packages import get_package_prefix
from launch import LaunchDescription
from launch.actions import (
    ExecuteProcess,
    SetEnvironmentVariable,
)
from launch_ros.actions import Node


def generate_launch_description():
    home = Path.home()

    world_file = (
        home
        / 'ball_launcher_ws'
        / 'src'
        / 'ball_launch_sim'
        / 'worlds'
        / 'heybeliada_ship_test.sdf'
    )

    models_directory = (
        home
        / 'ball_launcher_ws'
        / 'src'
        / 'ball_launch_sim'
        / 'models'
    )

    plugin_directory = (
        Path(
            get_package_prefix(
                'projectile_launch_plugin'
            )
        )
        / 'lib'
    )

    old_resource_path = os.environ.get(
        'GZ_SIM_RESOURCE_PATH',
        '',
    )

    old_plugin_path = os.environ.get(
        'GZ_SIM_SYSTEM_PLUGIN_PATH',
        '',
    )

    resource_path = str(models_directory)

    if old_resource_path:
        resource_path += (
            os.pathsep + old_resource_path
        )

    plugin_path = str(plugin_directory)

    if old_plugin_path:
        plugin_path += (
            os.pathsep + old_plugin_path
        )

    gazebo = ExecuteProcess(
        cmd=[
            'gz',
            'sim',
            '-v',
            '4',
            '-r',
            str(world_file),
        ],
        output='screen',
    )

    pan_tilt_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='heybeliada_pan_tilt_bridge',
        arguments=[
            (
                '/heybeliada/pan_cmd'
                '@std_msgs/msg/Float64'
                '@gz.msgs.Double'
            ),
            (
                '/heybeliada/tilt_cmd'
                '@std_msgs/msg/Float64'
                '@gz.msgs.Double'
            ),
        ],
        output='screen',
    )

    telemetry_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='heybeliada_telemetry_bridge',
        arguments=[
            (
                '/world/heybeliada_ship_test_world'
                '/model/heybeliada_ship/joint_state'
                '@sensor_msgs/msg/JointState'
                '[gz.msgs.Model'
            ),
        ],
        remappings=[
            (
                '/world/heybeliada_ship_test_world'
                '/model/heybeliada_ship/joint_state',
                '/joint_states',
            ),
        ],
        output='screen',
    )

    telemetry_node = Node(
        package='grpc_ros_bridge',
        executable='simulation_telemetry_node',
        name='simulation_telemetry_node',
        parameters=[
            {
                'platform_id': 'heybeliada_ship',
                'platform_x_m': 0.0,
                'platform_y_m': 0.0,
                'platform_z_m': 3.92,
                'platform_yaw_rad': 0.0,
            },
        ],
        output='screen',
    )

    gun_rate_controller = Node(
        package='ball_launch_sim',
        executable='gun_rate_controller',
        name='gun_rate_controller',
        output='screen',
    )

    ball_spawner = Node(
        package='ball_launch_sim',
        executable='ball_spawner',
        name='ball_spawner',
        parameters=[
            {
                'world_name':
                    'heybeliada_ship_test_world',

                'reference_model':
                    'heybeliada_ship',

                'reference_link':
                    'muzzle_link',

                'muzzle_clearance':
                    0.55,

                'ball_radius':
                    0.12,

                'ball_mass':
                    0.15,
            },
        ],
        output='screen',
    )

    fire_adapter = Node(
        package='ball_launch_sim',
        executable='fire_command_adapter',
        name='fire_command_adapter',
        output='screen',
    )

    grpc_server = Node(
        package='grpc_ros_bridge',
        executable='naval_bridge_server',
        name='naval_bridge_server',
        output='screen',
    )

    return LaunchDescription([
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=resource_path,
        ),

        SetEnvironmentVariable(
            name='GZ_SIM_SYSTEM_PLUGIN_PATH',
            value=plugin_path,
        ),

        gazebo,
        pan_tilt_bridge,
        telemetry_bridge,
        telemetry_node,
        gun_rate_controller,
        ball_spawner,
        fire_adapter,
        grpc_server,
    ])
