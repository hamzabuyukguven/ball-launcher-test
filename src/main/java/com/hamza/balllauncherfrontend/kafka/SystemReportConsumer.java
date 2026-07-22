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

public class SystemReportConsumer implements Runnable {

    private static final Logger logger = LoggerFactory.getLogger(SystemReportConsumer.class);
    private static final String REPORTS_TOPIC = "launcher.reports";

    private final KafkaConsumer<String, String> consumer;
    private final Consumer<SystemStatus> onReportReceived;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private volatile boolean running = true;

    public SystemReportConsumer(String bootstrapServers, String groupId, Consumer<SystemStatus> onReportReceived) {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");

        this.consumer = new KafkaConsumer<>(props);
        this.onReportReceived = onReportReceived;
    }

    @Override
    public void run() {
        consumer.subscribe(Collections.singletonList(REPORTS_TOPIC));
        logger.info("Subscribed to topic: {}", REPORTS_TOPIC);

        while (running) {
            ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
            for (ConsumerRecord<String, String> record : records) {
                String message = record.value();
                try {
                    SystemStatus report = objectMapper.readValue(message, SystemStatus.class);
                    Platform.runLater(() -> onReportReceived.accept(report));
                } catch (Exception e) {
                    logger.error("Failed to parse report message: {}", message, e);
                }
            }
        }
        consumer.close();
        logger.info("Report consumer closed.");
    }

    public void stop() {
        running = false;
    }
}