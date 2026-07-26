package com.hamza.balllauncherfrontend.kafka;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.hamza.balllauncherfrontend.AppConfig;
import javafx.application.Platform;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.errors.WakeupException;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.List;
import java.util.Properties;
import java.util.function.Consumer;

public class SystemStatusConsumer implements Runnable, AutoCloseable {
    private static final Logger logger = LoggerFactory.getLogger(SystemStatusConsumer.class);

    private final KafkaConsumer<String, String> consumer;
    private final ObjectMapper objectMapper;
    private final Consumer<SystemStatus> callback;
    private volatile boolean running = true;

    public SystemStatusConsumer(Consumer<SystemStatus> callback) {
        this.callback = callback;
        this.objectMapper = new ObjectMapper()
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, AppConfig.kafkaBootstrapServers());
        props.put(ConsumerConfig.GROUP_ID_CONFIG, AppConfig.statusGroupId());
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, true);
        props.put(ConsumerConfig.CLIENT_ID_CONFIG, "launcher-frontend-status-consumer");
        consumer = new KafkaConsumer<>(props);
    }

    @Override
    public void run() {
        consumer.subscribe(List.of(AppConfig.statusTopic(), AppConfig.telemetryTopic()));
        logger.info("Subscribed to status topics: {}, {}", AppConfig.statusTopic(), AppConfig.telemetryTopic());
        try {
            while (running && !Thread.currentThread().isInterrupted()) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(250));
                for (ConsumerRecord<String, String> record : records) {
                    try {
                        SystemStatus status = objectMapper.readValue(record.value(), SystemStatus.class);
                        Platform.runLater(() -> callback.accept(status));
                    } catch (Exception e) {
                        logger.warn("Invalid status payload on {}: {}", record.topic(), record.value(), e);
                    }
                }
            }
        } catch (WakeupException e) {
            if (running) {
                logger.warn("Status consumer woken unexpectedly", e);
            }
        } catch (Exception e) {
            logger.error("Status consumer failed", e);
        } finally {
            consumer.close();
        }
    }

    @Override
    public void close() {
        running = false;
        consumer.wakeup();
    }
}
