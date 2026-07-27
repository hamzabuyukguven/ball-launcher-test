package com.hamza.balllauncherfrontend.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.hamza.balllauncherfrontend.AppConfig;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;

public class CommandProducer implements AutoCloseable {

    private static final Logger logger = LoggerFactory.getLogger(CommandProducer.class);

    private final KafkaProducer<String, String> producer;
    private final ObjectMapper objectMapper = new ObjectMapper();

    private final String cmdTopic;
    private final String telemetryTopic;

    public CommandProducer(String bootstrapServers) {
        this.cmdTopic = AppConfig.commandTopic();
        this.telemetryTopic = AppConfig.telemetryTopic();

        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());

        // Simülasyoncunun eklediği harika güvenlik ve gecikme (latency) ayarları
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        props.put(ProducerConfig.RETRIES_CONFIG, Integer.MAX_VALUE);
        props.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, 10_000);
        props.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG, 3_000);
        props.put(ProducerConfig.CLIENT_ID_CONFIG, "launcher-frontend-command-producer");

        this.producer = new KafkaProducer<>(props);
    }

    public void sendCommand(LaunchCommand command) {
        try {
            String json = objectMapper.writeValueAsString(command);
            producer.send(new ProducerRecord<>(cmdTopic, json), (metadata, exception) -> {
                if (exception != null) {
                    logger.error("Failed to send command", exception);
                } else {
                    logger.info("Command sent to {}: {}", metadata.topic(), json);
                }
            });
        } catch (Exception e) {
            logger.error("Error serializing command", e);
        }
    }

    public void sendTelemetry(double targetX, double targetY) {
        try {
            LauncherTelemetry data = new LauncherTelemetry(targetX, targetY);
            String json = objectMapper.writeValueAsString(data);
            producer.send(new ProducerRecord<>(telemetryTopic, json), (metadata, exception) -> {
                if (exception != null) {
                    logger.error("Failed to send telemetry", exception);
                } else {
                    logger.info("Telemetry sent to {}: {}", metadata.topic(), json);
                }
            });
        } catch (Exception e) {
            logger.error("Error serializing telemetry", e);
        }
    }

    @Override
    public void close() {
        if (producer != null) {
            producer.flush();
            producer.close();
            logger.info("Producer closed.");
        }
    }
}

