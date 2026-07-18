#!/usr/bin/env python3

import argparse
import sys

import grpc

from . import naval_bridge_pb2
from . import naval_bridge_pb2_grpc


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            'Listen to Heybeliada simulation telemetry.'
        )
    )

    parser.add_argument(
        '--host',
        default='127.0.0.1',
    )

    parser.add_argument(
        '--port',
        type=int,
        default=50052,
    )

    parser.add_argument(
        '--client-id',
        default='python-telemetry-test-client',
    )

    parser.add_argument(
        '--count',
        type=int,
        default=20,
    )

    parser.add_argument(
        '--timeout',
        type=float,
        default=15.0,
    )

    return parser.parse_args()


def print_packet(packet) -> None:
    payload_type = packet.WhichOneof('payload')

    if payload_type == 'gun_info':
        message = packet.gun_info

        print(
            'GUN '
            f'seq={message.sequence} '
            f'pan={message.pan_angle_rad:.4f} '
            f'tilt={message.tilt_angle_rad:.4f} '
            f'cmd_pan={message.commanded_pan_rate_rad_s:.3f} '
            f'cmd_tilt={message.commanded_tilt_rate_rad_s:.3f} '
            f'ready={message.ready_to_fire} '
            f'firing={message.firing} '
            f'fault={message.fault}'
        )

    elif payload_type == 'platform_info':
        message = packet.platform_info

        print(
            'PLATFORM '
            f'seq={message.sequence} '
            f'position=('
            f'{message.position_x_m:.3f}, '
            f'{message.position_y_m:.3f}, '
            f'{message.position_z_m:.3f}) '
            f'yaw={message.yaw_rad:.4f} '
            f'ready={message.simulation_ready} '
            f'mode={message.mode}'
        )

    elif payload_type == 'heartbeat':
        message = packet.heartbeat

        print(
            'HEARTBEAT '
            f'seq={message.sequence} '
            f'component={message.component} '
            f'healthy={message.healthy} '
            f'state={message.state} '
            f'uptime={message.uptime_sec:.1f}'
        )

    else:
        print('UNKNOWN PACKET')


def main() -> None:
    arguments = parse_arguments()

    target = (
        f'{arguments.host}:{arguments.port}'
    )

    print(f'Connecting to {target}...')

    channel = grpc.insecure_channel(target)

    try:
        grpc.channel_ready_future(channel).result(
            timeout=5.0
        )

        stub = (
            naval_bridge_pb2_grpc
            .NavalBridgeServiceStub(channel)
        )

        request = naval_bridge_pb2.SubscribeRequest(
            client_id=arguments.client_id
        )

        stream = stub.StreamSimulationPackets(
            request,
            timeout=arguments.timeout,
        )

        print('Telemetry stream connected.')

        received = 0

        for packet in stream:
            print_packet(packet)

            received += 1

            if received >= arguments.count:
                stream.cancel()
                break

        print(
            f'Telemetry packets received: {received}'
        )

    except grpc.RpcError as error:
        print(
            f'gRPC error: {error.code().name}: '
            f'{error.details()}',
            file=sys.stderr,
        )
        raise SystemExit(1)

    except grpc.FutureTimeoutError:
        print(
            'Could not connect to the gRPC server.',
            file=sys.stderr,
        )
        raise SystemExit(1)

    finally:
        channel.close()


if __name__ == '__main__':
    main()
