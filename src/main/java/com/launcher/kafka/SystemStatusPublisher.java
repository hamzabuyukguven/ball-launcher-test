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

    private final String statusTopic;
    private final String telemetryTopic;
    private final String reportsTopic;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final KafkaProducer<String, String> producer;

    public SystemStatusPublisher(
            String bootstrapServers,
            String statusTopic,
            String telemetryTopic,
            String reportsTopic) {
        this.statusTopic = statusTopic;
        this.telemetryTopic = telemetryTopic;
        this.reportsTopic = reportsTopic;

        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        props.put(ProducerConfig.RETRIES_CONFIG, Integer.MAX_VALUE);
        props.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, 10_000);
        props.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG, 3_000);

        producer = new KafkaProducer<>(props);
        logger.info("Kafka publisher initialized for {}", bootstrapServers);
    }

    public void publishSystemStatus(SystemStatus status) {
        send(statusTopic, status);
    }

    public void publishTelemetry(SystemStatus status) {
        send(telemetryTopic, status);
    }

    public void publishReports(SystemStatus status) {
        send(reportsTopic, status);
    }

    private void send(String topic, SystemStatus status) {
        if (status == null) return;
        try {
            String json = objectMapper.writeValueAsString(status);
            producer.send(new ProducerRecord<>(topic, json), (metadata, exception) -> {
                if (exception != null) {
                    logger.error("Kafka publish failed for topic {}", topic, exception);
                }
            });
        } catch (Exception e) {
            logger.error("Could not serialize status for topic {}", topic, e);
        }
    }

    public void close() {
        producer.flush();
        producer.close();
    }
}
