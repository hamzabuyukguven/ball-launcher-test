#!/usr/bin/env python3

from concurrent import futures
import math
import queue
import threading
from typing import Optional

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
import rclpy
from naval_interfaces.msg import (
    FireCommand,
    GunInfo as RosGunInfo,
    GunRateCommand,
    GunStatusInfo as RosGunStatusInfo,
    Heartbeat as RosHeartbeat,
    PlatformPositionInfo as RosPlatformPositionInfo,
    PlatformStatusInfo as RosPlatformStatusInfo,
    PlatformVelocityInfo as RosPlatformVelocityInfo,
    StabilizationData as RosStabilizationData,
    TargetPositionInfo as RosTargetPositionInfo,
)
from rclpy.node import Node

from . import naval_bridge_pb2
from . import naval_bridge_pb2_grpc


GRPC_LISTEN_ADDRESS = '0.0.0.0:50052'
MAX_PAN_RATE = 0.35
MAX_TILT_RATE = 0.20


def current_timestamp() -> Timestamp:
    timestamp = Timestamp()
    timestamp.GetCurrentTime()
    return timestamp


def timestamp_is_valid(timestamp: Timestamp) -> bool:
    try:
        timestamp.ToNanoseconds()
        return True
    except (OverflowError, ValueError):
        return False


class TelemetryBroker:
    """Thread-safe fan-out broker for one telemetry category."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.subscribers = []
        self.latest_message = None

    def subscribe(self) -> queue.Queue:
        subscriber_queue = queue.Queue(maxsize=200)

        with self.lock:
            self.subscribers.append(subscriber_queue)
            latest_message = self.latest_message

        if latest_message is not None:
            subscriber_queue.put_nowait(latest_message)

        return subscriber_queue

    def unsubscribe(self, subscriber_queue: queue.Queue) -> None:
        with self.lock:
            if subscriber_queue in self.subscribers:
                self.subscribers.remove(subscriber_queue)

    def publish(self, message) -> None:
        with self.lock:
            self.latest_message = message
            subscribers = list(self.subscribers)

        for subscriber_queue in subscribers:
            try:
                subscriber_queue.put_nowait(message)
            except queue.Full:
                try:
                    subscriber_queue.get_nowait()
                except queue.Empty:
                    pass

                try:
                    subscriber_queue.put_nowait(message)
                except queue.Full:
                    pass


class NavalBridgeService(
    naval_bridge_pb2_grpc.NavalBridgeServiceServicer
):

    def __init__(
        self,
        gun_command_queue: queue.Queue,
        fire_command_queue: queue.Queue,
        target_position_broker: TelemetryBroker,
        gun_info_broker: TelemetryBroker,
        gun_status_broker: TelemetryBroker,
        platform_position_broker: TelemetryBroker,
        platform_velocity_broker: TelemetryBroker,
        stabilization_broker: TelemetryBroker,
        platform_status_broker: TelemetryBroker,
        heartbeat_broker: TelemetryBroker,
    ) -> None:
        self.gun_command_queue = gun_command_queue
        self.fire_command_queue = fire_command_queue
        self.target_position_broker = target_position_broker
        self.gun_info_broker = gun_info_broker
        self.gun_status_broker = gun_status_broker
        self.platform_position_broker = platform_position_broker
        self.platform_velocity_broker = platform_velocity_broker
        self.stabilization_broker = stabilization_broker
        self.platform_status_broker = platform_status_broker
        self.heartbeat_broker = heartbeat_broker

    @staticmethod
    def _command_reply(
        accepted: bool,
        message: str,
        sequence: int,
    ):
        return naval_bridge_pb2.CommandReply(
            accepted=accepted,
            message=message,
            sequence=sequence,
            timestamp=current_timestamp(),
        )

    def SendGunRateCommand(self, request, context):
        pan_rate = float(request.pan_rate)
        tilt_rate = float(request.tilt_rate)

        if not math.isfinite(pan_rate):
            return self._command_reply(
                False,
                'Pan rate must be a finite number.',
                request.sequence,
            )

        if not math.isfinite(tilt_rate):
            return self._command_reply(
                False,
                'Tilt rate must be a finite number.',
                request.sequence,
            )

        if abs(pan_rate) > MAX_PAN_RATE:
            return self._command_reply(
                False,
                'Pan rate is outside [-0.35, 0.35] rad/s.',
                request.sequence,
            )

        if abs(tilt_rate) > MAX_TILT_RATE:
            return self._command_reply(
                False,
                'Tilt rate is outside [-0.20, 0.20] rad/s.',
                request.sequence,
            )

        if not timestamp_is_valid(request.timestamp):
            return self._command_reply(
                False,
                'Timestamp is outside the protobuf Timestamp range.',
                request.sequence,
            )

        self.gun_command_queue.put(
            (
                int(request.sequence),
                pan_rate,
                tilt_rate,
                bool(request.control_enabled),
                request.timestamp,
            )
        )

        return self._command_reply(
            True,
            'Gun rate command was queued for ROS 2.',
            request.sequence,
        )

    def SendFireCommand(self, request, context):
        muzzle_velocity = float(request.muzzle_velocity)

        if not math.isfinite(muzzle_velocity):
            return self._command_reply(
                False,
                'Muzzle velocity must be a finite number.',
                request.sequence,
            )

        if muzzle_velocity <= 0.0:
            return self._command_reply(
                False,
                'Muzzle velocity must be greater than zero.',
                request.sequence,
            )

        if not timestamp_is_valid(request.timestamp):
            return self._command_reply(
                False,
                'Timestamp is outside the protobuf Timestamp range.',
                request.sequence,
            )

        self.fire_command_queue.put(
            (
                int(request.sequence),
                muzzle_velocity,
                request.timestamp,
            )
        )

        return self._command_reply(
            True,
            'Fire command was queued for the safety interlock.',
            request.sequence,
        )

    @staticmethod
    def _stream_from_broker(broker, context):
        subscriber_queue = broker.subscribe()

        try:
            while context.is_active():
                try:
                    message = subscriber_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                yield message
        finally:
            broker.unsubscribe(subscriber_queue)

    def StreamTargetPosition(self, request, context):
        yield from self._stream_from_broker(
            self.target_position_broker,
            context,
        )

    def StreamGunInfo(self, request, context):
        yield from self._stream_from_broker(
            self.gun_info_broker,
            context,
        )

    def StreamGunStatus(self, request, context):
        yield from self._stream_from_broker(
            self.gun_status_broker,
            context,
        )

    def StreamPlatformPosition(self, request, context):
        yield from self._stream_from_broker(
            self.platform_position_broker,
            context,
        )

    def StreamPlatformVelocity(self, request, context):
        yield from self._stream_from_broker(
            self.platform_velocity_broker,
            context,
        )

    def StreamStabilizationData(self, request, context):
        yield from self._stream_from_broker(
            self.stabilization_broker,
            context,
        )

    def StreamPlatformStatus(self, request, context):
        yield from self._stream_from_broker(
            self.platform_status_broker,
            context,
        )

    def StreamHeartbeat(self, request, context):
        yield from self._stream_from_broker(
            self.heartbeat_broker,
            context,
        )


class NavalBridgeServerNode(Node):

    def __init__(self) -> None:
        super().__init__('naval_bridge_server')

        self.gun_command_queue = queue.Queue()
        self.fire_command_queue = queue.Queue()
        self.target_position_broker = TelemetryBroker()
        self.gun_info_broker = TelemetryBroker()
        self.gun_status_broker = TelemetryBroker()
        self.platform_position_broker = TelemetryBroker()
        self.platform_velocity_broker = TelemetryBroker()
        self.stabilization_broker = TelemetryBroker()
        self.platform_status_broker = TelemetryBroker()
        self.heartbeat_broker = TelemetryBroker()

        self.gun_command_publisher = self.create_publisher(
            GunRateCommand,
            '/backend/gun_rate_command',
            10,
        )
        self.fire_command_publisher = self.create_publisher(
            FireCommand,
            '/backend/fire_command',
            10,
        )
        self.create_subscription(
            RosTargetPositionInfo,
            '/simulation/target_position',
            self.target_position_callback,
            10,
        )
        self.create_subscription(
            RosGunInfo,
            '/simulation/gun_info',
            self.gun_info_callback,
            10,
        )
        self.create_subscription(
            RosGunStatusInfo,
            '/simulation/gun_status',
            self.gun_status_callback,
            10,
        )
        self.create_subscription(
            RosPlatformPositionInfo,
            '/simulation/platform_position',
            self.platform_position_callback,
            10,
        )
        self.create_subscription(
            RosPlatformVelocityInfo,
            '/simulation/platform_velocity',
            self.platform_velocity_callback,
            10,
        )
        self.create_subscription(
            RosStabilizationData,
            '/simulation/stabilization_data',
            self.stabilization_callback,
            10,
        )
        self.create_subscription(
            RosPlatformStatusInfo,
            '/simulation/platform_status',
            self.platform_status_callback,
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
            self.fire_command_queue,
            self.target_position_broker,
            self.gun_info_broker,
            self.gun_status_broker,
            self.platform_position_broker,
            self.platform_velocity_broker,
            self.stabilization_broker,
            self.platform_status_broker,
            self.heartbeat_broker,
        )

        naval_bridge_pb2_grpc.add_NavalBridgeServiceServicer_to_server(
            service,
            self.grpc_server,
        )

        bound_port = self.grpc_server.add_insecure_port(
            GRPC_LISTEN_ADDRESS
        )
        if bound_port == 0:
            raise RuntimeError('gRPC could not bind to port 50052.')

        self.grpc_server.start()

        self.publish_timer = self.create_timer(
            0.01,
            self.publish_queued_messages,
        )

        self.get_logger().info('Naval bridge gRPC server v5 started.')
        self.get_logger().info(f'Listening on {GRPC_LISTEN_ADDRESS}')
        self.get_logger().info(
            'Command topics: /backend/gun_rate_command, '
            '/backend/fire_command'
        )
        self.get_logger().info(
            'Telemetry RPCs: StreamTargetPosition, '
            'StreamGunInfo, StreamGunStatus, '
            'StreamPlatformPosition, '
            'StreamPlatformVelocity, StreamStabilizationData, '
            'StreamPlatformStatus, StreamHeartbeat'
        )

    @staticmethod
    def protobuf_timestamp_from_ros(stamp) -> Timestamp:
        return Timestamp(
            seconds=int(stamp.sec),
            nanos=int(stamp.nanosec),
        )

    @staticmethod
    def copy_protobuf_timestamp_to_ros(source, destination) -> None:
        if source.seconds == 0 and source.nanos == 0:
            source = current_timestamp()

        destination.sec = int(source.seconds)
        destination.nanosec = int(source.nanos)

    def target_position_callback(
        self,
        message: RosTargetPositionInfo,
    ) -> None:
        grpc_message = naval_bridge_pb2.TargetPositionInfo(
            sequence=message.sequence,
            target_id=message.target_id,
            position_x=message.position_x,
            position_y=message.position_y,
            position_z=message.position_z,
            timestamp=self.protobuf_timestamp_from_ros(
                message.timestamp
            ),
        )
        self.target_position_broker.publish(grpc_message)

    def gun_info_callback(self, message: RosGunInfo) -> None:
        grpc_message = naval_bridge_pb2.GunInfo(
            sequence=message.sequence,
            gun_id=message.gun_id,
            pan_angle=message.pan_angle,
            tilt_angle=message.tilt_angle,
            pan_rate=message.pan_rate,
            tilt_rate=message.tilt_rate,
            timestamp=self.protobuf_timestamp_from_ros(
                message.timestamp
            ),
        )
        self.gun_info_broker.publish(grpc_message)

    def gun_status_callback(
        self,
        message: RosGunStatusInfo,
    ) -> None:
        grpc_message = naval_bridge_pb2.GunStatusInfo(
            sequence=message.sequence,
            gun_id=message.gun_id,
            control_enabled=message.control_enabled,
            ready_to_fire=message.ready_to_fire,
            firing=message.firing,
            fault=message.fault,
            fault_text=message.fault_text,
            timestamp=self.protobuf_timestamp_from_ros(
                message.timestamp
            ),
        )
        self.gun_status_broker.publish(grpc_message)

    def platform_position_callback(
        self,
        message: RosPlatformPositionInfo,
    ) -> None:
        grpc_message = naval_bridge_pb2.PlatformPositionInfo(
            sequence=message.sequence,
            platform_id=message.platform_id,
            position_x=message.position_x,
            position_y=message.position_y,
            position_z=message.position_z,
            timestamp=self.protobuf_timestamp_from_ros(
                message.timestamp
            ),
        )
        self.platform_position_broker.publish(grpc_message)

    def platform_velocity_callback(
        self,
        message: RosPlatformVelocityInfo,
    ) -> None:
        grpc_message = naval_bridge_pb2.PlatformVelocityInfo(
            sequence=message.sequence,
            platform_id=message.platform_id,
            velocity_x=message.velocity_x,
            velocity_y=message.velocity_y,
            velocity_z=message.velocity_z,
            timestamp=self.protobuf_timestamp_from_ros(
                message.timestamp
            ),
        )
        self.platform_velocity_broker.publish(grpc_message)

    def stabilization_callback(
        self,
        message: RosStabilizationData,
    ) -> None:
        grpc_message = naval_bridge_pb2.StabilizationData(
            sequence=message.sequence,
            platform_id=message.platform_id,
            roll=message.roll,
            pitch=message.pitch,
            yaw=message.yaw,
            roll_rate=message.roll_rate,
            pitch_rate=message.pitch_rate,
            yaw_rate=message.yaw_rate,
            timestamp=self.protobuf_timestamp_from_ros(
                message.timestamp
            ),
        )
        self.stabilization_broker.publish(grpc_message)

    def platform_status_callback(
        self,
        message: RosPlatformStatusInfo,
    ) -> None:
        grpc_message = naval_bridge_pb2.PlatformStatusInfo(
            sequence=message.sequence,
            platform_id=message.platform_id,
            simulation_ready=message.simulation_ready,
            mode=message.mode,
            timestamp=self.protobuf_timestamp_from_ros(
                message.timestamp
            ),
        )
        self.platform_status_broker.publish(grpc_message)

    def heartbeat_callback(self, message: RosHeartbeat) -> None:
        grpc_message = naval_bridge_pb2.Heartbeat(
            sequence=message.sequence,
            component=message.component,
            healthy=message.healthy,
            state=message.state,
            uptime=message.uptime,
            timestamp=self.protobuf_timestamp_from_ros(
                message.timestamp
            ),
        )
        self.heartbeat_broker.publish(grpc_message)

    def publish_queued_messages(self) -> None:
        self.publish_gun_commands()
        self.publish_fire_commands()

    def publish_gun_commands(self) -> None:
        while True:
            try:
                (
                    sequence,
                    pan_rate,
                    tilt_rate,
                    control_enabled,
                    timestamp,
                ) = self.gun_command_queue.get_nowait()
            except queue.Empty:
                return

            message = GunRateCommand()
            message.sequence = sequence
            message.pan_rate = pan_rate
            message.tilt_rate = tilt_rate
            message.control_enabled = control_enabled
            self.copy_protobuf_timestamp_to_ros(
                timestamp,
                message.timestamp,
            )
            self.gun_command_publisher.publish(message)

    def publish_fire_commands(self) -> None:
        while True:
            try:
                (
                    sequence,
                    muzzle_velocity,
                    timestamp,
                ) = self.fire_command_queue.get_nowait()
            except queue.Empty:
                return

            message = FireCommand()
            message.sequence = sequence
            message.muzzle_velocity = muzzle_velocity
            self.copy_protobuf_timestamp_to_ros(
                timestamp,
                message.timestamp,
            )
            self.fire_command_publisher.publish(message)

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
