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
import com.heybeliada.grpc.PlatformStatusInfo;
import com.heybeliada.grpc.StabilizationData;
import com.heybeliada.grpc.SubscribeRequest;
import com.heybeliada.grpc.TargetPositionInfo;
import io.grpc.ConnectivityState;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.StatusRuntimeException;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

public class NavalBridgeGrpcClient {
    private static final Logger logger = LoggerFactory.getLogger(NavalBridgeGrpcClient.class);
    private static final long STREAM_RETRY_SECONDS = 2L;

    private final ManagedChannel channel;
    private final NavalBridgeServiceGrpc.NavalBridgeServiceStub asyncStub;
    private final NavalBridgeServiceGrpc.NavalBridgeServiceBlockingStub blockingStub;
    private final SimulationDataProcessor dataProcessor;
    private final int deadlineMillis;
    private final ScheduledExecutorService retryExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread thread = new Thread(r, "grpc-stream-retry");
        thread.setDaemon(true);
        return thread;
    });
    private final AtomicBoolean streamsStarted = new AtomicBoolean(false);

    public NavalBridgeGrpcClient(
            String host,
            int port,
            int deadlineMillis,
            SimulationDataProcessor dataProcessor) {
        this.channel = ManagedChannelBuilder.forAddress(host, port)
                .usePlaintext()
                .keepAliveTime(10, TimeUnit.SECONDS)
                .keepAliveWithoutCalls(true)
                .build();
        this.asyncStub = NavalBridgeServiceGrpc.newStub(channel);
        this.blockingStub = NavalBridgeServiceGrpc.newBlockingStub(channel);
        this.dataProcessor = dataProcessor;
        this.deadlineMillis = deadlineMillis;
        logger.info("Simulation gRPC client configured for {}:{}", host, port);
    }

    public void startStreaming(String clientId) {
        if (!streamsStarted.compareAndSet(false, true)) {
            logger.debug("Simulation streams are already started");
            return;
        }

        SubscribeRequest request = SubscribeRequest.newBuilder().setClientId(clientId).build();
        logger.info("Subscribing to simulation streams as {}", clientId);

        subscribe("GunInfo", observer -> asyncStub.streamGunInfo(request, observer), dataProcessor::handleGunInfo);
        subscribe("GunStatus", observer -> asyncStub.streamGunStatus(request, observer), dataProcessor::handleGunStatus);
        subscribe("PlatformPosition", observer -> asyncStub.streamPlatformPosition(request, observer), dataProcessor::handlePlatformPosition);
        subscribe("TargetPosition", observer -> asyncStub.streamTargetPosition(request, observer), dataProcessor::handleTargetPosition);
        subscribe("StabilizationData", observer -> asyncStub.streamStabilizationData(request, observer), dataProcessor::handleStabilizationData);
        subscribe("PlatformStatus", observer -> asyncStub.streamPlatformStatus(request, observer), dataProcessor::handlePlatformStatus);
        subscribe("Heartbeat", observer -> asyncStub.streamHeartbeat(request, observer), dataProcessor::handleHeartbeat);
    }

    private <T> void subscribe(
            String streamName,
            Consumer<StreamObserver<T>> starter,
            Consumer<T> handler) {
        if (channel.isShutdown() || retryExecutor.isShutdown()) {
            return;
        }

        Runnable retry = () -> subscribe(streamName, starter, handler);
        try {
            starter.accept(observer(streamName, handler, retry));
        } catch (Exception e) {
            logger.warn("{} stream could not start: {}", streamName, e.getMessage());
            scheduleRetry(streamName, retry);
        }
    }

    private <T> StreamObserver<T> observer(
            String streamName,
            Consumer<T> handler,
            Runnable retry) {
        return new StreamObserver<>() {
            @Override
            public void onNext(T value) {
                try {
                    handler.accept(value);
                } catch (Exception e) {
                    logger.warn("{} message processing failed: {}", streamName, e.getMessage());
                }
            }

            @Override
            public void onError(Throwable throwable) {
                logger.warn("{} stream failed: {}", streamName, throwable.getMessage());
                scheduleRetry(streamName, retry);
            }

            @Override
            public void onCompleted() {
                logger.warn("{} stream completed; it will be reopened", streamName);
                scheduleRetry(streamName, retry);
            }
        };
    }

    private void scheduleRetry(String streamName, Runnable retry) {
        if (channel.isShutdown() || retryExecutor.isShutdown()) {
            return;
        }
        retryExecutor.schedule(() -> {
            if (!channel.isShutdown()) {
                logger.info("Reopening {} stream", streamName);
                retry.run();
            }
        }, STREAM_RETRY_SECONDS, TimeUnit.SECONDS);
    }

    public CommandReply sendGunRateCommand(double panRate, double tiltRate) {
        return sendGunRateCommand(panRate, tiltRate, true);
    }

    public CommandReply sendGunRateCommand(double panRate, double tiltRate, boolean controlEnabled) {
        long nowMs = System.currentTimeMillis();
        GunRateCommandRequest request = GunRateCommandRequest.newBuilder()
                .setSequence(nowMs)
                .setPanRate(panRate)
                .setTiltRate(tiltRate)
                .setControlEnabled(controlEnabled)
                .setTimestamp(timestamp(nowMs))
                .build();

        try {
            return blockingStub.withDeadlineAfter(deadlineMillis, TimeUnit.MILLISECONDS)
                    .sendGunRateCommand(request);
        } catch (StatusRuntimeException e) {
            logger.warn("Gun-rate command failed: {}", e.getStatus());
            return null;
        }
    }

    public CommandReply sendFireCommand(double muzzleVelocity) {
        long nowMs = System.currentTimeMillis();
        FireCommandRequest request = FireCommandRequest.newBuilder()
                .setSequence(nowMs)
                .setMuzzleVelocity(muzzleVelocity)
                .setTimestamp(timestamp(nowMs))
                .build();

        try {
            return blockingStub.withDeadlineAfter(deadlineMillis, TimeUnit.MILLISECONDS)
                    .sendFireCommand(request);
        } catch (StatusRuntimeException e) {
            logger.warn("Fire command failed: {}", e.getStatus());
            return null;
        }
    }

    public boolean isReady() {
        return channel.getState(true) == ConnectivityState.READY && !channel.isShutdown();
    }

    public void shutdown() {
        logger.info("Shutting down simulation gRPC channel");
        retryExecutor.shutdownNow();
        channel.shutdown();
        try {
            if (!channel.awaitTermination(5, TimeUnit.SECONDS)) {
                channel.shutdownNow();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            channel.shutdownNow();
        }
    }

    private static Timestamp timestamp(long nowMs) {
        return Timestamp.newBuilder()
                .setSeconds(nowMs / 1000)
                .setNanos((int) ((nowMs % 1000) * 1_000_000))
                .build();
    }
}
