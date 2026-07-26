package com.launcher;

import com.launcher.grpc.NavalBridgeGrpcClient;
import com.launcher.grpc.SimulationDataProcessor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class HeartbeatManager implements Runnable {
    private static final Logger logger = LoggerFactory.getLogger(HeartbeatManager.class);

    private final NavalBridgeGrpcClient grpcClient;
    private final SimulationDataProcessor dataProcessor;
    private final int intervalMillis;
    private volatile boolean running;
    private Thread workerThread;

    public HeartbeatManager(
            NavalBridgeGrpcClient grpcClient,
            SimulationDataProcessor dataProcessor,
            int intervalMillis) {
        this.grpcClient = grpcClient;
        this.dataProcessor = dataProcessor;
        this.intervalMillis = intervalMillis;
    }

    @Override
    public void run() {
        logger.info("Backend health publisher started");
        while (running && !Thread.currentThread().isInterrupted()) {
            dataProcessor.publishHealthSnapshot(grpcClient.isReady());
            try {
                Thread.sleep(intervalMillis);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        logger.info("Backend health publisher stopped");
    }

    public synchronized void start() {
        if (running) return;
        running = true;
        workerThread = new Thread(this, "heartbeat-publisher");
        workerThread.setDaemon(true);
        workerThread.start();
    }

    public synchronized void stop() {
        running = false;
        if (workerThread != null) {
            workerThread.interrupt();
        }
    }
}
