package com.launcher.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.launcher.kafka.model.SystemStatus;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;

public class SystemStatusPublisher {

    private static final Logger logger = LoggerFactory.getLogger(SystemStatusPublisher.class);

    private static final String STATUS_TOPIC = "launcher.status";
    private static final String TELEMETRY_TOPIC = "launcher.telemetry";
    private static final String REPORTS_TOPIC = "launcher.reports";

    private final ObjectMapper objectMapper;
    private final KafkaProducer<String, String> producer;

    public SystemStatusPublisher() {
        this("localhost:9092");
    }

    public SystemStatusPublisher(String bootStrapServers) {
        this.objectMapper = new ObjectMapper();

        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootStrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.RETRIES_CONFIG, 3);

        this.producer = new KafkaProducer<>(props);
        logger.info("Kafka system status publisher successfully initialized.");
    }

    public void publishSystemStatus(SystemStatus systemStatus) {
        sendToTopic(STATUS_TOPIC, systemStatus);
    }

    public void publishTelemetry(SystemStatus systemStatus) {
        sendToTopic(TELEMETRY_TOPIC, systemStatus);
    }

    public void publishReports(SystemStatus systemStatus) {
        sendToTopic(REPORTS_TOPIC, systemStatus);
    }

    public void sendToTopic(String topicName, SystemStatus systemStatus) {
        if (systemStatus == null) {
            logger.warn("Attempted to send null SystemStatus to topic [{}]", topicName);
            return;
        }

        try {
            String jsonStatus = objectMapper.writeValueAsString(systemStatus);
            ProducerRecord<String, String> record = new ProducerRecord<>(topicName, jsonStatus);

            producer.send(record, (metadata, exception) -> {
                if (exception != null) {
                    logger.error("ERROR: Status info couldn't be sent to topic [{}]", topicName, exception);
                } else {
                    logger.debug("Sent status to topic [{}]: {}", topicName, jsonStatus);
                }
            });

        } catch (Exception e) {
            logger.error("ERROR: JSON serialization error for topic [{}]", topicName, e);
        }
    }

    public void close() {
        if (producer != null) {
            logger.info("Closing Kafka system status publisher.");
            producer.close();
        }
    }
}
