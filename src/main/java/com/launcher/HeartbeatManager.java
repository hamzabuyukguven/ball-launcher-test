package com.launcher;

import com.launcher.grpc.NavalBridgeGrpcClient;
import com.launcher.kafka.SystemStatusPublisher;
import com.launcher.kafka.model.SystemStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class HeartbeatManager implements Runnable {

    private static final Logger logger = LoggerFactory.getLogger(HeartbeatManager.class);
    private final NavalBridgeGrpcClient grpcClient;
    private final SystemStatusPublisher statusPublisher;
    private final int intervalMillis = 5000;
    private volatile boolean running = true;
    private Thread workerThread;

    public HeartbeatManager(NavalBridgeGrpcClient grpcClient, SystemStatusPublisher statusPublisher) {
        this.grpcClient = grpcClient;
        this.statusPublisher = statusPublisher;
    }

    @Override
    public void run() {
        logger.info("System health monitoring started.");
        while (running && !Thread.currentThread().isInterrupted()) {
            try {
                checkSystemHealth();
                Thread.sleep(intervalMillis);
            } catch (InterruptedException e) {
                logger.info("System health monitoring thread was interrupted.");
                running = false;
                Thread.currentThread().interrupt();
            }
        }
    }

    private void checkSystemHealth() {
        boolean isGrpcAlive = (grpcClient != null);

        logger.info("gRPC Connection Status: " + (isGrpcAlive ? "ACTIVE" : "INACTIVE"));

        SystemStatus status = new SystemStatus(
                isGrpcAlive,
                isGrpcAlive ? "ACTIVE" : "INACTIVE",
                0.0,
                0.0,
                System.currentTimeMillis()
        );

        if (statusPublisher != null) {
            statusPublisher.publishSystemStatus(status);
        }
    }

    public void start() {
        logger.info("Starting system health monitoring system...");
        running = true;
        workerThread = new Thread(this, "Heartbeat-worker-thread");
        workerThread.start();
    }

    public void stop() {
        logger.info("Stopping system health monitoring system...");
        running = false;
        if (workerThread != null) {
            workerThread.interrupt();
        }
    }
}