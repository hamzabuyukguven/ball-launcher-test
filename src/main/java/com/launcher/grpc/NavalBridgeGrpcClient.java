package com.launcher.grpc;

import com.google.protobuf.Timestamp;
import com.heybeliada.grpc.CommandReply;
import com.heybeliada.grpc.FireCommandRequest;
import com.heybeliada.grpc.GunInfo;
import com.heybeliada.grpc.GunRateCommandRequest;
import com.heybeliada.grpc.GunStatusInfo;
import com.heybeliada.grpc.Heartbeat;
import com.heybeliada.grpc.NavalBridgeServiceGrpc;
import com.heybeliada.grpc.PlatformPositionInfo;
import com.heybeliada.grpc.SubscribeRequest;
import com.heybeliada.grpc.TargetPositionInfo;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.TimeUnit;

public class NavalBridgeGrpcClient {
    private static final Logger logger = LoggerFactory.getLogger(NavalBridgeGrpcClient.class);

    private final ManagedChannel channel;
    private final NavalBridgeServiceGrpc.NavalBridgeServiceStub asyncStub;
    private final NavalBridgeServiceGrpc.NavalBridgeServiceBlockingStub blockingStub;
    private final SimulationDataProcessor dataProcessor;

    public NavalBridgeGrpcClient(String host, int port, SimulationDataProcessor dataProcessor) {
        this.channel = ManagedChannelBuilder.forAddress(host, port)
                .usePlaintext()
                .build();
        this.asyncStub = NavalBridgeServiceGrpc.newStub(channel);
        this.blockingStub = NavalBridgeServiceGrpc.newBlockingStub(channel);
        this.dataProcessor = dataProcessor;
    }

    public void startStreaming(String clientId) {
        SubscribeRequest request = SubscribeRequest.newBuilder()
                .setClientId(clientId)
                .build();

        logger.info("Subscribing to simulation gRPC streams (Client ID: {})...", clientId);

        asyncStub.streamGunInfo(request, new StreamObserver<GunInfo>() {
            @Override
            public void onNext(GunInfo gunInfo) {
                dataProcessor.handleGunInfo(gunInfo);
            }

            @Override
            public void onError(Throwable t) {
                logger.error("GunInfo stream error: ", t);
            }

            @Override
            public void onCompleted() {
                logger.info("GunInfo stream closed.");
            }
        });

        asyncStub.streamGunStatus(request, new StreamObserver<GunStatusInfo>() {
            @Override
            public void onNext(GunStatusInfo gunStatus) {
                dataProcessor.handleGunStatus(gunStatus);
            }

            @Override
            public void onError(Throwable t) {
                logger.error("GunStatus stream error: ", t);
            }

            @Override
            public void onCompleted() {
                logger.info("GunStatus stream closed.");
            }
        });

        asyncStub.streamPlatformPosition(request, new StreamObserver<PlatformPositionInfo>() {
            @Override
            public void onNext(PlatformPositionInfo platformPosition) {
                dataProcessor.handlePlatformPosition(platformPosition);
            }

            @Override
            public void onError(Throwable t) {
                logger.error("PlatformPosition stream error: ", t);
            }

            @Override
            public void onCompleted() {
                logger.info("PlatformPosition stream closed.");
            }
        });

        asyncStub.streamTargetPosition(request, new StreamObserver<TargetPositionInfo>() {
            @Override
            public void onNext(TargetPositionInfo targetPosition) {
                dataProcessor.handleTargetPosition(targetPosition);
            }

            @Override
            public void onError(Throwable t) {
                logger.error("TargetPosition stream error: ", t);
            }

            @Override
            public void onCompleted() {
                logger.info("TargetPosition stream closed.");
            }
        });

        asyncStub.streamHeartbeat(request, new StreamObserver<Heartbeat>() {
            @Override
            public void onNext(Heartbeat heartbeat) {
                dataProcessor.handleHeartbeat(heartbeat);
            }

            @Override
            public void onError(Throwable t) {
                logger.error("Heartbeat stream error: ", t);
            }

            @Override
            public void onCompleted() {
                logger.info("Heartbeat stream closed.");
            }
        });
    }

    public CommandReply sendGunRateCommand(double panRate, double tiltRate) {
        long nowMs = System.currentTimeMillis();
        Timestamp timestamp = Timestamp.newBuilder()
                .setSeconds(nowMs / 1000)
                .setNanos((int) ((nowMs % 1000) * 1000000))
                .build();

        GunRateCommandRequest request = GunRateCommandRequest.newBuilder()
                .setSequence(nowMs)
                .setPanRate(panRate)
                .setTiltRate(tiltRate)
                .setControlEnabled(true)
                .setTimestamp(timestamp)
                .build();

        return blockingStub.sendGunRateCommand(request);
    }

    public CommandReply sendFireCommand(double muzzleVelocity) {
        long nowMs = System.currentTimeMillis();
        Timestamp timestamp = Timestamp.newBuilder()
                .setSeconds(nowMs / 1000)
                .setNanos((int) ((nowMs % 1000) * 1000000))
                .build();

        FireCommandRequest request = FireCommandRequest.newBuilder()
                .setSequence(nowMs)
                .setMuzzleVelocity(muzzleVelocity)
                .setTimestamp(timestamp)
                .build();

        return blockingStub.sendFireCommand(request);
    }

    public void shutdown() {
        try {
            logger.info("Shutting down gRPC channel...");
            channel.shutdown().awaitTermination(5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            logger.error("Interrupted while shutting down gRPC channel", e);
        }
    }
}