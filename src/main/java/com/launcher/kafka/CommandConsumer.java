package com.launcher.kafka;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.launcher.kafka.model.LaunchCommand;
import com.launcher.kafka.model.LauncherTelemetry;
import com.launcher.simulationtest.LauncherControlService;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.errors.WakeupException;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.Collections;
import java.util.Locale;
import java.util.Properties;

public class CommandConsumer implements Runnable {
    private static final Logger logger = LoggerFactory.getLogger(CommandConsumer.class);

    private final String commandTopic;
    private final KafkaConsumer<String, String> consumer;
    private final ObjectMapper objectMapper;
    private final LauncherControlService controlService;
    private volatile boolean running = true;

    public CommandConsumer(
            String bootstrapServers,
            String commandTopic,
            String groupId,
            LauncherControlService controlService) {
        this.commandTopic = commandTopic;
        this.controlService = controlService;
        this.objectMapper = new ObjectMapper()
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, true);
        props.put(ConsumerConfig.CLIENT_ID_CONFIG, "launcher-backend-command-consumer");
        consumer = new KafkaConsumer<>(props);
    }

    @Override
    public void run() {
        consumer.subscribe(Collections.singletonList(commandTopic));
        logger.info("Listening for frontend commands on {}", commandTopic);
        try {
            while (running && !Thread.currentThread().isInterrupted()) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(250));
                for (ConsumerRecord<String, String> record : records) {
                    try {
                        LaunchCommand command = objectMapper.readValue(record.value(), LaunchCommand.class);
                        processCommand(command);
                    } catch (Exception e) {
                        logger.warn("Invalid command payload: {}", record.value(), e);
                    }
                }
            }
        } catch (WakeupException e) {
            if (running) {
                logger.warn("Kafka consumer was woken unexpectedly", e);
            }
        } catch (Exception e) {
            logger.error("Kafka command consumer failed", e);
        } finally {
            consumer.close();
            logger.info("Kafka command consumer closed");
        }
    }

    private void processCommand(LaunchCommand command) {
        if (command == null || command.getAction() == null || command.getAction().isBlank()) {
            logger.warn("Command ignored because action is missing");
            return;
        }

        String action = command.getAction().trim().toUpperCase(Locale.ROOT);
        LauncherTelemetry telemetry = command.getTelemetry();
        logger.info("Frontend command received: {}", action);

        switch (action) {
            case "SET_MANUAL_TARGET" -> {
                if (telemetry == null) {
                    logger.warn("SET_MANUAL_TARGET requires telemetry coordinates");
                } else {
                    controlService.processTargetTelemetry(telemetry);
                }
            }
            case "USE_TRACKED_TARGET" -> controlService.useTrackedTarget();
            case "FIRE" -> controlService.requestFire(telemetry);
            case "STOW" -> controlService.moveToStowPosition();
            case "EMERGENCY_STOP" -> controlService.emergencyStop();
            case "CLEAR_EMERGENCY_STOP" -> controlService.clearEmergencyStop();
            default -> logger.warn("Unknown frontend action: {}", action);
        }
    }

    public void stop() {
        running = false;
        consumer.wakeup();
    }
}
