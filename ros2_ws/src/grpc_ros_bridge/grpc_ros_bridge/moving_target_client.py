#!/usr/bin/env python3
import grpc

from . import moving_target_pb2
from . import moving_target_pb2_grpc


def read_number(prompt: str) -> float:
    while True:
        value = input(prompt).strip().replace(',', '.')
        try:
            return float(value)
        except ValueError:
            print('Geçerli bir sayı gir. Örnek: 3000')


def main() -> None:
    channel = grpc.insecure_channel('localhost:50052')
    stub = moving_target_pb2_grpc.LauncherCommandServiceStub(channel)

    print('Top lançer komut istemcisi')
    print('x-y metre, motor hızları RPM cinsindedir.')
    print('Tek motor kullanıyorsan iki RPM alanına da aynı değeri gir.')
    print('Çıkmak için Ctrl+C.')

    try:
        while True:
            print('\nYeni atış komutu:')
            x = read_number('Hedef x (m): ')
            y = read_number('Hedef y (m): ')
            left_motor_rpm = read_number('Sol fırlatma motoru (RPM): ')
            right_motor_rpm = read_number('Sağ fırlatma motoru (RPM): ')

            try:
                reply = stub.SendCommand(
                    moving_target_pb2.LauncherCommandRequest(
                        x=x,
                        y=y,
                        left_motor_rpm=left_motor_rpm,
                        right_motor_rpm=right_motor_rpm,
                    ),
                    timeout=5.0,
                )
                print(reply.message)
            except grpc.RpcError as exc:
                print('gRPC bağlantı hatası:', exc.details())
    except KeyboardInterrupt:
        print('\nİstemci kapatıldı.')


if __name__ == '__main__':
    main()
