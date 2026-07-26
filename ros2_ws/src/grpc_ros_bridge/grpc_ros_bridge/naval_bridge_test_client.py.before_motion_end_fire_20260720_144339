#!/usr/bin/env python3

import argparse
import math
import time

import grpc

from . import naval_bridge_pb2
from . import naval_bridge_pb2_grpc


def finite_number(value: str) -> float:
    number = float(value)

    if not math.isfinite(number):
        raise argparse.ArgumentTypeError(
            'The value must be a finite number.'
        )

    return number


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Send gun rate commands over gRPC.'
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
        '--pan-rate',
        type=finite_number,
        default=0.0,
    )

    parser.add_argument(
        '--tilt-rate',
        type=finite_number,
        default=0.0,
    )

    parser.add_argument(
        '--duration',
        type=finite_number,
        default=3.0,
    )

    parser.add_argument(
        '--rate',
        type=finite_number,
        default=20.0,
    )

    parser.add_argument(
        '--fire',
        action='store_true',
    )

    args = parser.parse_args()

    if args.rate <= 0.0:
        raise SystemExit(
            'ERROR: Rate must be greater than zero.'
        )

    if args.duration <= 0.0:
        raise SystemExit(
            'ERROR: Duration must be greater than zero.'
        )

    if abs(args.pan_rate) > 0.35:
        raise SystemExit(
            'ERROR: Pan rate range is -0.35 to 0.35 rad/s.'
        )

    if abs(args.tilt_rate) > 0.20:
        raise SystemExit(
            'ERROR: Tilt rate range is -0.20 to 0.20 rad/s.'
        )

    address = f'{args.host}:{args.port}'

    channel = grpc.insecure_channel(address)

    print(f'Connecting to {address}...')

    try:
        grpc.channel_ready_future(channel).result(
            timeout=5.0
        )
    except grpc.FutureTimeoutError:
        channel.close()

        raise SystemExit(
            f'ERROR: Could not connect to {address}.'
        )

    print('Connected.')

    stub = naval_bridge_pb2_grpc.NavalBridgeServiceStub(
        channel
    )

    sequence = 1
    period = 1.0 / args.rate
    end_time = time.monotonic() + args.duration

    fire_pending = args.fire
    sent_count = 0

    try:
        while time.monotonic() < end_time:
            request = naval_bridge_pb2.GunRateCommandRequest(
                sequence=sequence,
                pan_rate_rad_s=args.pan_rate,
                tilt_rate_rad_s=args.tilt_rate,
                control_enabled=True,
                fire=fire_pending,
                timestamp_ms=int(time.time() * 1000),
            )

            reply = stub.SendGunRateCommand(
                request,
                timeout=2.0,
            )

            if not reply.accepted:
                raise SystemExit(
                    f'Command rejected: {reply.message}'
                )

            fire_pending = False
            sequence += 1
            sent_count += 1

            time.sleep(period)

        stop_request = (
            naval_bridge_pb2.GunRateCommandRequest(
                sequence=sequence,
                pan_rate_rad_s=0.0,
                tilt_rate_rad_s=0.0,
                control_enabled=False,
                fire=False,
                timestamp_ms=int(time.time() * 1000),
            )
        )

        stop_reply = stub.SendGunRateCommand(
            stop_request,
            timeout=2.0,
        )

        if not stop_reply.accepted:
            raise SystemExit(
                f'Stop command rejected: '
                f'{stop_reply.message}'
            )

        print(f'Command packets sent: {sent_count}')
        print(
            'Command completed and an explicit '
            'stop command was sent.'
        )

    except grpc.RpcError as error:
        raise SystemExit(
            f'gRPC error: '
            f'{error.code().name}: {error.details()}'
        )

    finally:
        channel.close()


if __name__ == '__main__':
    main()
