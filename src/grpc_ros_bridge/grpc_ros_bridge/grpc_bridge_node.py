#!/usr/bin/env python3

from concurrent import futures
from queue import Empty, Queue
import threading

import grpc
import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node

from grpc_ros_bridge import target_pb2
from grpc_ros_bridge import target_pb2_grpc


class TargetService(target_pb2_grpc.TargetServiceServicer):
    """
    gRPC üzerinden gelen koordinatları karşılayan servis.

    Bu sınıf doğrudan ROS topic'ine yayın yapmak yerine gelen
    koordinatları güvenli bir kuyruğa bırakır.
    """

    def __init__(self, target_queue: Queue):
        self.target_queue = target_queue

    def SendTarget(self, request, context):
        x = request.x
        y = request.y

        print(f"[gRPC] Yeni hedef geldi: x={x:.2f}, y={y:.2f}")

        # Koordinatı ROS node'unun okuyacağı kuyruğa bırak.
        self.target_queue.put((x, y))

        return target_pb2.TargetResponse(
            success=True,
            message=f"Hedef alındı: x={x:.2f}, y={y:.2f}",
        )


class GrpcRosBridgeNode(Node):
    """
    Kuyruktaki gRPC koordinatlarını alıp ROS 2 topic'ine yayınlar.
    """

    def __init__(self):
        super().__init__("grpc_ros_bridge")

        self.publisher = self.create_publisher(
            Point,
            "/target_coordinates",
            10,
        )

        self.target_queue = Queue()

        # Kuyruğu her 0.05 saniyede bir kontrol et.
        self.timer = self.create_timer(
            0.05,
            self.publish_pending_targets,
        )

        self.grpc_server = None

        self.get_logger().info(
            "gRPC-ROS köprüsü başlatılıyor..."
        )

    def start_grpc_server(self):
        self.grpc_server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=4)
        )

        target_service = TargetService(self.target_queue)

        target_pb2_grpc.add_TargetServiceServicer_to_server(
            target_service,
            self.grpc_server,
        )

        # [::] bütün ağ arayüzlerini, 50051 ise portu belirtir.
        self.grpc_server.add_insecure_port("[::]:50051")
        self.grpc_server.start()

        self.get_logger().info(
            "gRPC sunucusu 50051 portunda çalışıyor."
        )

    def publish_pending_targets(self):
        while True:
            try:
                x, y = self.target_queue.get_nowait()
            except Empty:
                break

            ros_message = Point()
            ros_message.x = float(x)
            ros_message.y = float(y)
            ros_message.z = 0.0

            self.publisher.publish(ros_message)

            self.get_logger().info(
                f"ROS topic'ine yayınlandı: x={x:.2f}, y={y:.2f}"
            )

    def stop_grpc_server(self):
        if self.grpc_server is not None:
            self.grpc_server.stop(grace=1)
            self.get_logger().info("gRPC sunucusu durduruldu.")


def main(args=None):
    rclpy.init(args=args)

    node = GrpcRosBridgeNode()

    # gRPC sunucusunu ayrı bir thread içinde başlatıyoruz.
    grpc_thread = threading.Thread(
        target=node.start_grpc_server,
        daemon=True,
    )
    grpc_thread.start()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Program kullanıcı tarafından durduruldu.")
    finally:
        node.stop_grpc_server()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
