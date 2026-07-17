package com.hamza.balllauncherfrontend.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import javafx.application.Platform;

import java.time.Duration;
import java.util.Collections;
import java.util.Properties;
import java.util.function.Consumer;

public class SystemStatusConsumer implements Runnable {

    private static final Logger logger = LoggerFactory.getLogger(SystemStatusConsumer.class);
    private static final String STATUS_TOPIC = "status";

    private final KafkaConsumer<String, String> consumer;
    private final Consumer<SystemStatus> onStatusReceived;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private volatile boolean running = true;

    public SystemStatusConsumer(String bootstrapServers, String groupId, Consumer<SystemStatus> onStatusReceived) {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");

        this.consumer = new KafkaConsumer<>(props);
        this.onStatusReceived = onStatusReceived;
    }

    @Override
    public void run() {
        consumer.subscribe(Collections.singletonList(STATUS_TOPIC));
        logger.info("Subscribed to topic: {}", STATUS_TOPIC);

        while (running) {
            ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
            for (ConsumerRecord<String, String> record : records) {
                String message = record.value();
                try {
                    SystemStatus status = objectMapper.readValue(message, SystemStatus.class);
                    Platform.runLater(() -> onStatusReceived.accept(status));
                } catch (Exception e) {
                    logger.error("Failed to parse status message: {}", message, e);
                }
            }
        }
        consumer.close();
        logger.info("Consumer closed.");
    }

    public void stop() {
        running = false;
    }
}
