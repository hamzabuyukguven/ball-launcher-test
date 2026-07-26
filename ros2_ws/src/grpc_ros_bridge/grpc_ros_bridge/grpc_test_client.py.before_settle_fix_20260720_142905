#!/usr/bin/env python3

import grpc

from grpc_ros_bridge import target_pb2
from grpc_ros_bridge import target_pb2_grpc


def main():
    print("gRPC test istemcisi")
    print("ROS sistemine gönderilecek koordinatları gir.")

    try:
        x = float(input("X koordinatı: "))
        y = float(input("Y koordinatı: "))
    except ValueError:
        print("Hata: X ve Y için sayı girmelisin.")
        return

    # localhost: Bu bilgisayardaki gRPC sunucusuna bağlan.
    # 50051: Sunucunun dinlediği port.
    with grpc.insecure_channel("localhost:50051") as channel:
        client = target_pb2_grpc.TargetServiceStub(channel)

        request = target_pb2.TargetRequest(
            x=x,
            y=y,
        )

        try:
            response = client.SendTarget(
                request,
                timeout=5.0,
            )
        except grpc.RpcError as error:
            print("gRPC bağlantı hatası:")
            print(error.details())
            return

    print("\nSunucudan cevap geldi:")
    print(f"Başarılı mı?: {response.success}")
    print(f"Mesaj: {response.message}")


if __name__ == "__main__":
    main()
