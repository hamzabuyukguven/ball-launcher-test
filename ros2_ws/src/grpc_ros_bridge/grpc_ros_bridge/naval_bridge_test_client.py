#!/usr/bin/env python3

import argparse
import math
import time

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from grpc_ros_bridge import naval_bridge_pb2
from grpc_ros_bridge import naval_bridge_pb2_grpc


def finite_number(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError('Value must be finite.')
    return number


def now_timestamp() -> Timestamp:
    timestamp = Timestamp()
    timestamp.GetCurrentTime()
    return timestamp


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Test separated movement and fire RPCs over gRPC.'
        )
    )
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=50052)
    parser.add_argument('--pan-rate', type=finite_number, default=0.0)
    parser.add_argument('--tilt-rate', type=finite_number, default=0.0)
    parser.add_argument(
        '--muzzle-velocity',
        type=finite_number,
        default=18.0,
        help='Projectile muzzle velocity in m/s.',
    )
    parser.add_argument('--duration', type=finite_number, default=3.0)
    parser.add_argument('--rate', type=finite_number, default=20.0)
    parser.add_argument('--fire', action='store_true')
    args = parser.parse_args()

    if args.muzzle_velocity <= 0.0:
        raise SystemExit('ERROR: Muzzle velocity must be positive.')
    if args.rate <= 0.0:
        raise SystemExit('ERROR: Rate must be positive.')
    if args.duration <= 0.0:
        raise SystemExit('ERROR: Duration must be positive.')
    if abs(args.pan_rate) > 0.35:
        raise SystemExit('ERROR: Pan rate range is -0.35 to 0.35 rad/s.')
    if abs(args.tilt_rate) > 0.20:
        raise SystemExit('ERROR: Tilt rate range is -0.20 to 0.20 rad/s.')

    address = f'{args.host}:{args.port}'
    channel = grpc.insecure_channel(address)
    print(f'Connecting to {address}...')

    try:
        grpc.channel_ready_future(channel).result(timeout=5.0)
    except grpc.FutureTimeoutError:
        channel.close()
        raise SystemExit(f'ERROR: Could not connect to {address}.')

    print('Connected.')
    stub = naval_bridge_pb2_grpc.NavalBridgeServiceStub(channel)
    movement_sequence = 1
    fire_sequence = 1
    period = 1.0 / args.rate
    movement_end_time = time.monotonic() + args.duration
    fire_sent = False
    movement_packet_count = 0

    try:
        while time.monotonic() < movement_end_time:
            movement_request = naval_bridge_pb2.GunRateCommandRequest(
                sequence=movement_sequence,
                pan_rate=args.pan_rate,
                tilt_rate=args.tilt_rate,
                control_enabled=True,
                timestamp=now_timestamp(),
            )
            movement_reply = stub.SendGunRateCommand(
                movement_request,
                timeout=2.0,
            )
            if not movement_reply.accepted:
                raise SystemExit(
                    f'Movement command rejected: {movement_reply.message}'
                )

            # Fire is a separate category and is sent exactly once.
            if args.fire and not fire_sent:
                fire_request = naval_bridge_pb2.FireCommandRequest(
                    sequence=fire_sequence,
                    muzzle_velocity=args.muzzle_velocity,
                    timestamp=now_timestamp(),
                )
                fire_reply = stub.SendFireCommand(
                    fire_request,
                    timeout=2.0,
                )
                if not fire_reply.accepted:
                    raise SystemExit(
                        f'Fire command rejected: {fire_reply.message}'
                    )
                print('Fire command queued separately from movement.')
                fire_sent = True

            movement_sequence += 1
            movement_packet_count += 1
            time.sleep(period)

        print('Movement completed. Waiting for gun settling...')
        settle_end_time = time.monotonic() + 2.0
        settle_packet_count = 0

        while time.monotonic() < settle_end_time:
            settle_request = naval_bridge_pb2.GunRateCommandRequest(
                sequence=movement_sequence,
                pan_rate=0.0,
                tilt_rate=0.0,
                control_enabled=True,
                timestamp=now_timestamp(),
            )
            settle_reply = stub.SendGunRateCommand(
                settle_request,
                timeout=2.0,
            )
            if not settle_reply.accepted:
                raise SystemExit(
                    f'Settle command rejected: {settle_reply.message}'
                )
            movement_sequence += 1
            settle_packet_count += 1
            time.sleep(period)

        disable_request = naval_bridge_pb2.GunRateCommandRequest(
            sequence=movement_sequence,
            pan_rate=0.0,
            tilt_rate=0.0,
            control_enabled=False,
            timestamp=now_timestamp(),
        )
        disable_reply = stub.SendGunRateCommand(
            disable_request,
            timeout=2.0,
        )
        if not disable_reply.accepted:
            raise SystemExit(
                f'Disable command rejected: {disable_reply.message}'
            )

        print(f'Movement packets sent: {movement_packet_count}')
        print(f'Settling packets sent: {settle_packet_count}')
        print('Movement, optional fire, settling and disable completed.')

    except grpc.RpcError as error:
        raise SystemExit(
            f'gRPC error: {error.code().name}: {error.details()}'
        )
    finally:
        channel.close()


if __name__ == '__main__':
    main()
