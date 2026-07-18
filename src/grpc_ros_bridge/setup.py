from setuptools import find_packages, setup

package_name = "grpc_ros_bridge"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        (
            "share/" + package_name,
            ["package.xml"],
        ),
    ],
    install_requires=[
        "setuptools",
    ],
    zip_safe=True,
    maintainer="fatih",
    maintainer_email="ayabakanfatih@gmail.com",
    description="gRPC koordinat mesajlarını ROS 2 topic mesajlarına çevirir.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            'naval_bridge_server = grpc_ros_bridge.naval_bridge_server:main',
            'naval_telemetry_test_client = grpc_ros_bridge.naval_telemetry_test_client:main',
            'simulation_telemetry_node = grpc_ros_bridge.simulation_telemetry_node:main',
            'naval_bridge_test_client = grpc_ros_bridge.naval_bridge_test_client:main',
            'moving_target_bridge = grpc_ros_bridge.moving_target_bridge_node:main',
            'moving_target_client = grpc_ros_bridge.moving_target_client:main',
            "grpc_bridge = grpc_ros_bridge.grpc_bridge_node:main",
            "grpc_client = grpc_ros_bridge.grpc_test_client:main",
        ],
    },
)
