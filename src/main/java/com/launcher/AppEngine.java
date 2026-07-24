package com.launcher;

import com.launcher.config.AppConfig;
import com.launcher.grpc.NavalBridgeGrpcClient;
import com.launcher.grpc.SimulationDataProcessor;
import com.launcher.kafka.CommandConsumer;
import com.launcher.kafka.SystemStatusPublisher;
import com.launcher.simulationtest.LauncherControlService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AppEngine {

    private static final Logger logger = LoggerFactory.getLogger(AppEngine.class);

    private final AppConfig config;
    private final SystemStatusPublisher statusPublisher;
    private final CommandConsumer commandConsumer;
    private final HeartbeatManager heartbeatManager;

    private final NavalBridgeGrpcClient grpcClient;
    private final SimulationDataProcessor dataProcessor;
    private final LauncherControlService controlService;

    public AppEngine() {
        this.config = new AppConfig();

        String bootStrapServers = config.getKafkaBootstrapServers();
        logger.info("Connecting to Kafka Bootstrap Servers: {}", bootStrapServers);

        this.statusPublisher = new SystemStatusPublisher(bootStrapServers);
        this.dataProcessor = new SimulationDataProcessor(statusPublisher);

        String grpcHost = "172.20.10.6";
        int grpcPort = 50052;
        this.grpcClient = new NavalBridgeGrpcClient(grpcHost, grpcPort, dataProcessor);

        this.controlService = new LauncherControlService(grpcClient);
        this.dataProcessor.setControlService(controlService);

        this.commandConsumer = new CommandConsumer(bootStrapServers, this.controlService);

        this.heartbeatManager = new HeartbeatManager(grpcClient, this.statusPublisher);
    }

    public void start() {
        logger.info("Starting AppEngine services...");

        if (grpcClient != null) {
            logger.info("Starting gRPC Streams...");
            grpcClient.startStreaming("app_engine_client");
        }

        if (commandConsumer != null) {
            Thread consumerThread = new Thread(commandConsumer, "Kafka-Consumer-Thread");
            consumerThread.start();
        }

        if (heartbeatManager != null) {
            heartbeatManager.start();
        }

        logger.info("AppEngine successfully initialized with all components.");
    }

    public void stop() {
        logger.info("Stopping AppEngine...");

        if (heartbeatManager != null) {
            heartbeatManager.stop();
        }

        if (commandConsumer != null) {
            commandConsumer.stop();
        }

        if (grpcClient != null) {
            grpcClient.shutdown();
        }

        if (statusPublisher != null) {
            statusPublisher.close();
        }

        logger.info("AppEngine stopped.");
    }

    public LauncherControlService getControlService() {
        return controlService;
    }

    public NavalBridgeGrpcClient getGrpcClient() {
        return grpcClient;
    }
}