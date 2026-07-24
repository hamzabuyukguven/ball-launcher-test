package com.launcher.kafka;

import java.lang.Runnable;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.launcher.kafka.model.LaunchCommand;
import com.launcher.kafka.model.LauncherTelemetry;
import com.launcher.simulationtest.LauncherControlService;
import org.apache.kafka.common.errors.WakeupException;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.Properties;
import java.util.Collections;

public class CommandConsumer implements Runnable {
    public static final Logger logger = LoggerFactory.getLogger(CommandConsumer.class);

    private static final String COMMAND_TOPIC = "launcher.commands";
    private final KafkaConsumer<String, String> consumer;
    private final ObjectMapper objectMapper;
    private final LauncherControlService controlService;
    private volatile boolean running = true;

    public CommandConsumer(LauncherControlService controlService) {
        this("172.20.10.3:9092", controlService);
    }

    public CommandConsumer(String bootstrapServers, LauncherControlService controlService) {
        this.objectMapper = new ObjectMapper();
        this.controlService = controlService;

        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "launcher-group");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");

        this.consumer = new KafkaConsumer<>(props);
    }

    @Override
    public void run() {
        consumer.subscribe(Collections.singletonList(COMMAND_TOPIC));
        logger.info("Listening on Kafka topic [{}], Waiting for commands...", COMMAND_TOPIC);

        try {
            while (running && !Thread.currentThread().isInterrupted()) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
                for (ConsumerRecord<String, String> record : records) {
                    try {
                        LaunchCommand command = objectMapper.readValue(record.value(), LaunchCommand.class);
                        processCommand(command);
                    } catch (Exception e) {
                        logger.warn("Failed to parse command payload: {}", e.getMessage());
                    }
                }
            }
        } catch (WakeupException e) {
            logger.info("Kafka consumer received wakeup signal.");
        } catch (Exception e) {
            logger.error("Unexpected error in Kafka consumer thread: ", e);
        } finally {
            try {
                consumer.close();
                logger.info("Kafka consumer successfully closed.");
            } catch (Exception e) {
                logger.error("Error closing Kafka consumer: ", e);
            }
        }
    }

    private void processCommand(LaunchCommand command) {
        if (command == null || command.getAction() == null) {
            logger.warn("Received null command or action.");
            return;
        }

        String action = command.getAction().toUpperCase();

        LauncherTelemetry telemetry = command.getTelemetry();
        double targetX = (telemetry != null) ? telemetry.getTargetX() : 0.0;
        double targetY = (telemetry != null) ? telemetry.getTargetY() : 0.0;

        logger.info("Received command >>> Action: {}, TargetX: {}, TargetY: {}", action, targetX, targetY);

        switch (action) {
            case "SET_MANUAL_TARGET":
                logger.info("Setting manual target coordinates: X = {}, Y = {}", targetX, targetY);
                if (controlService != null) {
                    controlService.updateTargetPosition(targetX, targetY);
                }
                break;

            case "FIRE":
                logger.info("Firing at target : X = {}, Y = {}", targetX, targetY);
                if (controlService != null) {
                    controlService.fire();
                }
                break;

            case "STOW":
                logger.info("Moving launcher to STOW Position...");
                if (controlService != null) {
                    controlService.moveToStowPosition();
                }
                break;

            case "EMERGENCY_STOP":
                logger.warn("!!! EMERGENCY STOP COMMAND RECIEVED !!!");
                if (controlService != null) {
                    controlService.emergencyStop();
                }
                break;

            default:
                logger.warn("Received unknown command: {}", action);
                break;
        }
    }

    public void stop() {
        logger.info("Stopping Kafka command consumer...");
        this.running = false;
        if (this.consumer != null) {
            this.consumer.wakeup();
        }
    }
}