#!/usr/bin/env python3
from concurrent import futures
import queue
from typing import Optional

import grpc
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

from . import moving_target_pb2
from . import moving_target_pb2_grpc


class LauncherCommandService(
    moving_target_pb2_grpc.LauncherCommandServiceServicer
):
    def __init__(self, command_queue: queue.Queue) -> None:
        self.command_queue = command_queue

    def SendCommand(self, request, context):
        values = (
            float(request.x),
            float(request.y),
            float(request.left_motor_rpm),
            float(request.right_motor_rpm),
        )
        self.command_queue.put(values)
        return moving_target_pb2.LauncherCommandReply(
            accepted=True,
            message='Lançer komutu ROS 2 kuyruğuna alındı.',
        )


class LauncherCommandBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__('launcher_command_grpc_bridge')
        self.publisher = self.create_publisher(
            Float64MultiArray,
            '/launcher_command',
            10,
        )
        self.command_queue: queue.Queue = queue.Queue()
        self.timer = self.create_timer(0.02, self.publish_queued_command)

        self.grpc_server: Optional[grpc.Server] = grpc.server(
            futures.ThreadPoolExecutor(max_workers=4)
        )
        moving_target_pb2_grpc.add_LauncherCommandServiceServicer_to_server(
            LauncherCommandService(self.command_queue),
            self.grpc_server,
        )
        self.grpc_server.add_insecure_port('0.0.0.0:50052')
        self.grpc_server.start()
        self.get_logger().info(
            'gRPC lançer sunucusu 0.0.0.0:50052 üzerinde hazır.'
        )

    def publish_queued_command(self) -> None:
        try:
            x, y, left_rpm, right_rpm = self.command_queue.get_nowait()
        except queue.Empty:
            return

        msg = Float64MultiArray()
        msg.data = [x, y, left_rpm, right_rpm]
        self.publisher.publish(msg)
        self.get_logger().info(
            'ROS 2 yayını: x=%.2f m, y=%.2f m, sol motor=%.0f RPM, sağ motor=%.0f RPM'
            % (x, y, left_rpm, right_rpm)
        )

    def destroy_node(self):
        if self.grpc_server is not None:
            self.grpc_server.stop(grace=0)
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LauncherCommandBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
