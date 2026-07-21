package com.launcher;

import com.launcher.tcp.TCPLauncher;
import com.launcher.config.AppConfig;
import com.launcher.kafka.CommandConsumer;
import com.launcher.kafka.SystemStatusPublisher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AppEngine {

    private static final Logger logger = LoggerFactory.getLogger(AppEngine.class);
    private final AppConfig config;
    private final TCPLauncher tcpLauncher;
    private final HeartbeatManager heartbeatManager;
    private final SystemStatusPublisher statusPublisher;
    private final CommandConsumer commandConsumer;

    public AppEngine(){
        this.config = new AppConfig();

        this.tcpLauncher = new TCPLauncher(config);
        String bootStrapServers = config.getKafkaBootstrapServers();
        logger.info("Connecting to Kafka Bootstrap Servers: {}", bootStrapServers);
        this.statusPublisher = new SystemStatusPublisher(bootStrapServers);
        this.commandConsumer = new CommandConsumer(bootStrapServers);
        this.heartbeatManager = new HeartbeatManager(tcpLauncher, this.statusPublisher);
    }
    public void start() {
        if (tcpLauncher != null) {
            logger.info("Initiating network communication...");
            tcpLauncher.start();
        }

        if (tcpLauncher != null && tcpLauncher.isActive()) {
            logger.info("TCP Connection Established");
        }

        if (commandConsumer != null) {
            Thread consumerThread = new Thread(() -> {
                try {
                    commandConsumer.run();
                } catch (Exception e) {
                    logger.error("Error in Kafka Command Consumer Thread: ", e);
                }
            });
            consumerThread.setName("Kafka-Consumer-Thread");
            consumerThread.start();
        }

        if (heartbeatManager != null) {
            heartbeatManager.start();
        } else {
            logger.error("TCP Connection is failed.");
        }
    }

    public void stop() {

        if (tcpLauncher != null) {
            tcpLauncher.stop();
        }

        if(statusPublisher != null){
            statusPublisher.close();
        }

        if (heartbeatManager != null) {
            heartbeatManager.stop();
        }

        if (commandConsumer != null) {
            commandConsumer.stop();
        }
    }
}