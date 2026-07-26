#!/usr/bin/env python3

import argparse
import queue
import sys
import threading

import grpc

from . import naval_bridge_pb2
from . import naval_bridge_pb2_grpc


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Listen to separated Heybeliada telemetry streams.'
    )
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=50052)
    parser.add_argument('--client-id', default='python-telemetry-test-client')
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--timeout', type=float, default=15.0)
    parser.add_argument(
        '--stream',
        choices=(
            'all',
            'target',
            'gun',
            'gun_status',
            'position',
            'velocity',
            'stabilization',
            'status',
            'heartbeat',
        ),
        default='all',
    )
    return parser.parse_args()


def format_target(message) -> str:
    return (
        'TARGET '
        f'seq={message.sequence} '
        f'target={message.target_id} '
        f'xyz=({message.position_x:.3f}, '
        f'{message.position_y:.3f}, {message.position_z:.3f})'
    )


def format_gun(message) -> str:
    return (
        'GUN '
        f'seq={message.sequence} '
        f'pan={message.pan_angle:.4f} '
        f'tilt={message.tilt_angle:.4f} '
        f'pan_rate={message.pan_rate:.4f} '
        f'tilt_rate={message.tilt_rate:.4f}'
    )


def format_gun_status(message) -> str:
    return (
        'GUN_STATUS '
        f'seq={message.sequence} '
        f'gun={message.gun_id} '
        f'control={message.control_enabled} '
        f'ready={message.ready_to_fire} '
        f'firing={message.firing} '
        f'fault={message.fault} '
        f'fault_text={message.fault_text!r}'
    )


def format_position(message) -> str:
    return (
        'POSITION '
        f'seq={message.sequence} '
        f'platform={message.platform_id} '
        f'xyz=({message.position_x:.3f}, '
        f'{message.position_y:.3f}, {message.position_z:.3f})'
    )


def format_velocity(message) -> str:
    return (
        'VELOCITY '
        f'seq={message.sequence} '
        f'platform={message.platform_id} '
        f'vxyz=({message.velocity_x:.3f}, '
        f'{message.velocity_y:.3f}, {message.velocity_z:.3f})'
    )


def format_stabilization(message) -> str:
    return (
        'STABILIZATION '
        f'seq={message.sequence} '
        f'roll={message.roll:.4f} '
        f'pitch={message.pitch:.4f} '
        f'yaw={message.yaw:.4f} '
        f'roll_rate={message.roll_rate:.4f} '
        f'pitch_rate={message.pitch_rate:.4f} '
        f'yaw_rate={message.yaw_rate:.4f}'
    )


def format_status(message) -> str:
    return (
        'STATUS '
        f'seq={message.sequence} '
        f'platform={message.platform_id} '
        f'ready={message.simulation_ready} '
        f'mode={message.mode}'
    )


def format_heartbeat(message) -> str:
    return (
        'HEARTBEAT '
        f'seq={message.sequence} '
        f'component={message.component} '
        f'healthy={message.healthy} '
        f'state={message.state} '
        f'uptime={message.uptime:.1f}'
    )


def main() -> None:
    arguments = parse_arguments()
    target = f'{arguments.host}:{arguments.port}'
    print(f'Connecting to {target}...')
    channel = grpc.insecure_channel(target)

    try:
        grpc.channel_ready_future(channel).result(timeout=5.0)
        stub = naval_bridge_pb2_grpc.NavalBridgeServiceStub(channel)
        request = naval_bridge_pb2.SubscribeRequest(
            client_id=arguments.client_id
        )

        stream_specs = {
            'target': (
                stub.StreamTargetPosition,
                format_target,
            ),
            'gun': (stub.StreamGunInfo, format_gun),
            'gun_status': (
                stub.StreamGunStatus,
                format_gun_status,
            ),
            'position': (
                stub.StreamPlatformPosition,
                format_position,
            ),
            'velocity': (
                stub.StreamPlatformVelocity,
                format_velocity,
            ),
            'stabilization': (
                stub.StreamStabilizationData,
                format_stabilization,
            ),
            'status': (
                stub.StreamPlatformStatus,
                format_status,
            ),
            'heartbeat': (stub.StreamHeartbeat, format_heartbeat),
        }
        selected = (
            tuple(stream_specs.keys())
            if arguments.stream == 'all'
            else (arguments.stream,)
        )

        output_queue = queue.Queue()
        stop_event = threading.Event()
        streams = []

        def worker(name, rpc, formatter):
            try:
                stream = rpc(request, timeout=arguments.timeout)
                streams.append(stream)
                for message in stream:
                    if stop_event.is_set():
                        break
                    output_queue.put((name, formatter(message), None))
            except grpc.RpcError as error:
                if not stop_event.is_set():
                    output_queue.put((name, None, error))

        threads = []
        for name in selected:
            rpc, formatter = stream_specs[name]
            thread = threading.Thread(
                target=worker,
                args=(name, rpc, formatter),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        print('Telemetry stream(s) connected: ' + ', '.join(selected))
        received = 0

        while received < arguments.count:
            name, text, error = output_queue.get(
                timeout=arguments.timeout
            )
            if error is not None:
                raise error
            print(text)
            received += 1

        stop_event.set()
        for stream in streams:
            stream.cancel()

        print(f'Telemetry messages received: {received}')

    except queue.Empty:
        print('Telemetry timeout.', file=sys.stderr)
        raise SystemExit(1)
    except grpc.RpcError as error:
        print(
            f'gRPC error: {error.code().name}: {error.details()}',
            file=sys.stderr,
        )
        raise SystemExit(1)
    except grpc.FutureTimeoutError:
        print('Could not connect to the gRPC server.', file=sys.stderr)
        raise SystemExit(1)
    finally:
        channel.close()


if __name__ == '__main__':
    main()
