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
    private Thread commandConsumerThread;
    private volatile boolean started;

    public AppEngine() {
        config = new AppConfig();

        String kafkaServers = config.getKafkaBootstrapServers();
        statusPublisher = new SystemStatusPublisher(
                kafkaServers,
                config.getKafkaStatusTopic(),
                config.getKafkaTelemetryTopic(),
                config.getKafkaReportsTopic());

        dataProcessor = new SimulationDataProcessor(statusPublisher);
        grpcClient = new NavalBridgeGrpcClient(
                config.getGrpcHost(),
                config.getGrpcPort(),
                config.getGrpcDeadlineMillis(),
                dataProcessor);

        controlService = new LauncherControlService(grpcClient, config);
        dataProcessor.setControlService(controlService);

        commandConsumer = new CommandConsumer(
                kafkaServers,
                config.getKafkaCommandTopic(),
                config.getKafkaConsumerGroupId(),
                controlService);

        heartbeatManager = new HeartbeatManager(
                grpcClient,
                dataProcessor,
                config.getHeartbeatPublishIntervalMillis());
    }

    public synchronized void start() {
        if (started) return;
        started = true;

        logger.info("Starting backend: Kafka={}, simulation={}:{}",
                config.getKafkaBootstrapServers(),
                config.getGrpcHost(),
                config.getGrpcPort());

        controlService.start();
        grpcClient.startStreaming(config.getGrpcClientId());

        commandConsumerThread = new Thread(commandConsumer, "kafka-command-consumer");
        commandConsumerThread.setDaemon(true);
        commandConsumerThread.start();

        heartbeatManager.start();
        logger.info("Backend started successfully");
    }

    public synchronized void stop() {
        if (!started) return;
        started = false;
        logger.info("Stopping backend");

        heartbeatManager.stop();
        commandConsumer.stop();
        controlService.stop();
        grpcClient.shutdown();
        statusPublisher.close();

        if (commandConsumerThread != null) {
            try {
                commandConsumerThread.join(2000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        logger.info("Backend stopped");
    }

    public LauncherControlService getControlService() {
        return controlService;
    }

    public AppConfig getConfig() {
        return config;
    }
}
