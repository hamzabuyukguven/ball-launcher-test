#!/usr/bin/env python3

from concurrent import futures
import math
import queue
import threading
from typing import Optional

import grpc
import rclpy
from naval_interfaces.msg import (
    GunInfo as RosGunInfo,
    GunRateCommand,
    Heartbeat as RosHeartbeat,
    PlatformInfo as RosPlatformInfo,
    TargetInfo,
)
from rclpy.node import Node

from . import naval_bridge_pb2
from . import naval_bridge_pb2_grpc


GRPC_LISTEN_ADDRESS = '0.0.0.0:50052'

MAX_PAN_RATE_RAD_S = 0.35
MAX_TILT_RATE_RAD_S = 0.20


class TelemetryBroker:

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.subscribers = []
        self.latest_packets = {}

    def subscribe(self) -> queue.Queue:
        subscriber_queue = queue.Queue(maxsize=200)

        with self.lock:
            self.subscribers.append(subscriber_queue)
            latest = list(self.latest_packets.values())

        for packet in latest:
            try:
                subscriber_queue.put_nowait(packet)
            except queue.Full:
                break

        return subscriber_queue

    def unsubscribe(
        self,
        subscriber_queue: queue.Queue,
    ) -> None:
        with self.lock:
            if subscriber_queue in self.subscribers:
                self.subscribers.remove(
                    subscriber_queue
                )

    def publish(
        self,
        packet_type: str,
        packet,
    ) -> None:
        with self.lock:
            self.latest_packets[packet_type] = packet
            subscribers = list(self.subscribers)

        for subscriber_queue in subscribers:
            try:
                subscriber_queue.put_nowait(packet)
            except queue.Full:
                try:
                    subscriber_queue.get_nowait()
                except queue.Empty:
                    pass

                try:
                    subscriber_queue.put_nowait(packet)
                except queue.Full:
                    pass


class NavalBridgeService(
    naval_bridge_pb2_grpc.NavalBridgeServiceServicer
):

    def __init__(
        self,
        gun_command_queue: queue.Queue,
        target_queue: queue.Queue,
        telemetry_broker: TelemetryBroker,
    ) -> None:
        self.gun_command_queue = gun_command_queue
        self.target_queue = target_queue
        self.telemetry_broker = telemetry_broker

    def SendGunRateCommand(self, request, context):
        pan_rate = float(request.pan_rate_rad_s)
        tilt_rate = float(request.tilt_rate_rad_s)

        if not math.isfinite(pan_rate):
            return naval_bridge_pb2.CommandReply(
                accepted=False,
                message='Pan rate must be a finite number.',
                sequence=request.sequence,
            )

        if not math.isfinite(tilt_rate):
            return naval_bridge_pb2.CommandReply(
                accepted=False,
                message='Tilt rate must be a finite number.',
                sequence=request.sequence,
            )

        if abs(pan_rate) > MAX_PAN_RATE_RAD_S:
            return naval_bridge_pb2.CommandReply(
                accepted=False,
                message=(
                    'Pan rate is outside the allowed range '
                    '[-0.35, 0.35] rad/s.'
                ),
                sequence=request.sequence,
            )

        if abs(tilt_rate) > MAX_TILT_RATE_RAD_S:
            return naval_bridge_pb2.CommandReply(
                accepted=False,
                message=(
                    'Tilt rate is outside the allowed range '
                    '[-0.20, 0.20] rad/s.'
                ),
                sequence=request.sequence,
            )

        self.gun_command_queue.put(
            (
                int(request.sequence),
                pan_rate,
                tilt_rate,
                bool(request.control_enabled),
                bool(request.fire),
            )
        )

        return naval_bridge_pb2.CommandReply(
            accepted=True,
            message='Gun rate command was queued for ROS 2.',
            sequence=request.sequence,
        )

    def SendTargetInfo(self, request, context):
        position_x = float(request.position_x_m)
        position_y = float(request.position_y_m)
        position_z = float(request.position_z_m)
        confidence = float(request.confidence)

        values = [
            position_x,
            position_y,
            confidence,
        ]

        if request.has_position_z:
            values.append(position_z)

        if not all(math.isfinite(value) for value in values):
            return naval_bridge_pb2.CommandReply(
                accepted=False,
                message='Target values must be finite.',
                sequence=request.sequence,
            )

        self.target_queue.put(
            (
                int(request.sequence),
                str(request.target_id),
                position_x,
                position_y,
                bool(request.has_position_z),
                position_z,
                confidence,
                bool(request.valid),
            )
        )

        return naval_bridge_pb2.CommandReply(
            accepted=True,
            message='Target information was queued for ROS 2.',
            sequence=request.sequence,
        )

    def StreamSimulationPackets(
        self,
        request,
        context,
    ):
        subscriber_queue = (
            self.telemetry_broker.subscribe()
        )

        try:
            while context.is_active():
                try:
                    packet = subscriber_queue.get(
                        timeout=1.0
                    )
                except queue.Empty:
                    continue

                yield packet
        finally:
            self.telemetry_broker.unsubscribe(
                subscriber_queue
            )


class NavalBridgeServerNode(Node):

    def __init__(self) -> None:
        super().__init__('naval_bridge_server')

        self.gun_command_queue = queue.Queue()
        self.target_queue = queue.Queue()

        self.telemetry_broker = TelemetryBroker()

        self.gun_info_sequence = 0
        self.platform_info_sequence = 0

        self.gun_command_publisher = self.create_publisher(
            GunRateCommand,
            '/backend/gun_rate_command',
            10,
        )

        self.target_publisher = self.create_publisher(
            TargetInfo,
            '/backend/target_info',
            10,
        )

        self.create_subscription(
            RosGunInfo,
            '/simulation/gun_info',
            self.gun_info_callback,
            10,
        )

        self.create_subscription(
            RosPlatformInfo,
            '/simulation/platform_info',
            self.platform_info_callback,
            10,
        )

        self.create_subscription(
            RosHeartbeat,
            '/simulation/heartbeat',
            self.heartbeat_callback,
            10,
        )

        self.grpc_server: Optional[grpc.Server] = grpc.server(
            futures.ThreadPoolExecutor(max_workers=16)
        )

        service = NavalBridgeService(
            self.gun_command_queue,
            self.target_queue,
            self.telemetry_broker,
        )

        naval_bridge_pb2_grpc.add_NavalBridgeServiceServicer_to_server(
            service,
            self.grpc_server,
        )

        bound_port = self.grpc_server.add_insecure_port(
            GRPC_LISTEN_ADDRESS
        )

        if bound_port == 0:
            raise RuntimeError(
                'gRPC could not bind to port 50052.'
            )

        self.grpc_server.start()

        self.publish_timer = self.create_timer(
            0.01,
            self.publish_queued_messages,
        )

        self.get_logger().info(
            'Naval bridge gRPC server started.'
        )
        self.get_logger().info(
            f'Listening on {GRPC_LISTEN_ADDRESS}'
        )
        self.get_logger().info(
            'Telemetry RPC: StreamSimulationPackets'
        )

    @staticmethod
    def timestamp_ms(stamp) -> int:
        return (
            int(stamp.sec) * 1000
            + int(stamp.nanosec) // 1_000_000
        )

    def gun_info_callback(
        self,
        message: RosGunInfo,
    ) -> None:
        self.gun_info_sequence += 1

        grpc_message = naval_bridge_pb2.GunInfo(
            sequence=self.gun_info_sequence,
            gun_id=message.gun_id,
            pan_angle_rad=message.pan_angle_rad,
            tilt_angle_rad=message.tilt_angle_rad,
            pan_rate_rad_s=message.pan_rate_rad_s,
            tilt_rate_rad_s=message.tilt_rate_rad_s,
            commanded_pan_rate_rad_s=(
                message.commanded_pan_rate_rad_s
            ),
            commanded_tilt_rate_rad_s=(
                message.commanded_tilt_rate_rad_s
            ),
            control_enabled=message.control_enabled,
            ready_to_fire=message.ready_to_fire,
            firing=message.firing,
            fault=message.fault,
            fault_text=message.fault_text,
            timestamp_ms=self.timestamp_ms(
                message.header.stamp
            ),
        )

        packet = naval_bridge_pb2.SimulationPacket(
            gun_info=grpc_message
        )

        self.telemetry_broker.publish(
            'gun_info',
            packet,
        )

    def platform_info_callback(
        self,
        message: RosPlatformInfo,
    ) -> None:
        self.platform_info_sequence += 1

        grpc_message = naval_bridge_pb2.PlatformInfo(
            sequence=self.platform_info_sequence,
            platform_id=message.platform_id,
            position_x_m=message.position_x_m,
            position_y_m=message.position_y_m,
            position_z_m=message.position_z_m,
            velocity_x_mps=message.velocity_x_mps,
            velocity_y_mps=message.velocity_y_mps,
            velocity_z_mps=message.velocity_z_mps,
            yaw_rad=message.yaw_rad,
            yaw_rate_rad_s=message.yaw_rate_rad_s,
            simulation_ready=message.simulation_ready,
            mode=message.mode,
            timestamp_ms=self.timestamp_ms(
                message.header.stamp
            ),
        )

        packet = naval_bridge_pb2.SimulationPacket(
            platform_info=grpc_message
        )

        self.telemetry_broker.publish(
            'platform_info',
            packet,
        )

    def heartbeat_callback(
        self,
        message: RosHeartbeat,
    ) -> None:
        grpc_message = naval_bridge_pb2.Heartbeat(
            sequence=message.sequence,
            component=message.component,
            healthy=message.healthy,
            state=message.state,
            uptime_sec=message.uptime_sec,
            timestamp_ms=self.timestamp_ms(
                message.header.stamp
            ),
        )

        packet = naval_bridge_pb2.SimulationPacket(
            heartbeat=grpc_message
        )

        self.telemetry_broker.publish(
            'heartbeat',
            packet,
        )

    def publish_queued_messages(self) -> None:
        self.publish_gun_commands()
        self.publish_target_information()

    def publish_gun_commands(self) -> None:
        while True:
            try:
                (
                    sequence,
                    pan_rate,
                    tilt_rate,
                    control_enabled,
                    fire,
                ) = self.gun_command_queue.get_nowait()
            except queue.Empty:
                return

            message = GunRateCommand()

            message.header.stamp = (
                self.get_clock().now().to_msg()
            )
            message.header.frame_id = 'heybeliada_ship'

            message.sequence = sequence
            message.pan_rate_rad_s = pan_rate
            message.tilt_rate_rad_s = tilt_rate
            message.control_enabled = control_enabled
            message.fire = fire

            self.gun_command_publisher.publish(message)

    def publish_target_information(self) -> None:
        while True:
            try:
                (
                    _sequence,
                    target_id,
                    position_x,
                    position_y,
                    has_position_z,
                    position_z,
                    confidence,
                    valid,
                ) = self.target_queue.get_nowait()
            except queue.Empty:
                return

            message = TargetInfo()

            message.header.stamp = (
                self.get_clock().now().to_msg()
            )
            message.header.frame_id = 'world'

            message.target_id = target_id
            message.position_x_m = position_x
            message.position_y_m = position_y
            message.has_position_z = has_position_z
            message.position_z_m = position_z
            message.confidence = confidence
            message.valid = valid

            self.target_publisher.publish(message)

    def destroy_node(self) -> bool:
        if self.grpc_server is not None:
            self.grpc_server.stop(grace=0)

        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)

    node = NavalBridgeServerNode()

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
