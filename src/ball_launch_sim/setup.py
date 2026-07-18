import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'ball_launch_sim'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
        (os.path.join('share', package_name, 'models', 'ball_launcher'),
         glob('models/ball_launcher/*')),
        (os.path.join('share', package_name, 'models', 'ball'),
         glob('models/ball/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Fatih Ayabakan',
    maintainer_email='ayabakanfatih@gmail.com',
    description='Moving-target ballistic launcher simulation for ROS 2 Jazzy and Gazebo Harmonic.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'fire_command_adapter = ball_launch_sim.fire_command_adapter:main',
            'gun_rate_controller = ball_launch_sim.gun_rate_controller:main',
            'ballistic_controller = ball_launch_sim.ballistic_controller:main',
            'ball_spawner = ball_launch_sim.ball_spawner:main',
        ],
    },
)
