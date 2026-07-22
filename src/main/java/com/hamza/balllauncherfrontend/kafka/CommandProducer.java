package com.hamza.balllauncherfrontend.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;

public class CommandProducer {

    private static final Logger logger = LoggerFactory.getLogger(CommandProducer.class);
    private static final String CMD_TOPIC = "launcher.commands";
    private static final String TELEMETRY_TOPIC = "launcher.telemetry";

    private final KafkaProducer<String, String> producer;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public CommandProducer(String bootstrapServers) {
        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());

        this.producer = new KafkaProducer<>(props);
    }

    public void sendCommand(LaunchCommand command) {
        try {
            String json = objectMapper.writeValueAsString(command);
            producer.send(new ProducerRecord<>(CMD_TOPIC, json), (metadata, exception) -> {
                if (exception != null) {
                    logger.error("Failed to send command", exception);
                } else {
                    logger.info("Command sent: {}", json);
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
            producer.send(new ProducerRecord<>(TELEMETRY_TOPIC, json), (metadata, exception) -> {
                if (exception != null) {
                    logger.error("Failed to send telemetry", exception);
                } else {
                    logger.info("Telemetry sent: {}", json);
                }
            });
        } catch (Exception e) {
            logger.error("Error serializing telemetry", e);
        }
    }

    public void close() {
        if (producer != null) {
            producer.close();
            logger.info("Producer closed.");
        }
    }
}

 
