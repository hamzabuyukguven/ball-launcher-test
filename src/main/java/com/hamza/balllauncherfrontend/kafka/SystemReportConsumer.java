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
import java.util.Collections;
import java.util.Properties;
import java.util.function.Consumer;

public class SystemReportConsumer implements Runnable {

    private static final Logger logger = LoggerFactory.getLogger(SystemReportConsumer.class);

    private final KafkaConsumer<String, String> consumer;
    private final ObjectMapper objectMapper;
    private final Consumer<SystemStatus> onReportReceived;
    private volatile boolean running = true;
    private final String reportsTopic;

    public SystemReportConsumer(String bootstrapServers, String groupId, Consumer<SystemStatus> onReportReceived) {
        this.onReportReceived = onReportReceived;
        this.reportsTopic = AppConfig.reportsTopic();

        this.objectMapper = new ObjectMapper()
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");

        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, true);
        props.put(ConsumerConfig.CLIENT_ID_CONFIG, "launcher-frontend-report-consumer");

        this.consumer = new KafkaConsumer<>(props);
    }

    @Override
    public void run() {
        consumer.subscribe(Collections.singletonList(reportsTopic));
        logger.info("Subscribed to reports topic: {}", reportsTopic);

        try {
            while (running && !Thread.currentThread().isInterrupted()) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(250));
                for (ConsumerRecord<String, String> record : records) {
                    try {
                        SystemStatus report = objectMapper.readValue(record.value(), SystemStatus.class);
                        Platform.runLater(() -> onReportReceived.accept(report));
                    } catch (Exception e) {
                        logger.warn("Invalid report payload: {}", record.value(), e);
                    }
                }
            }
        } catch (WakeupException e) {
            if (running) {
                logger.warn("Report consumer woken unexpectedly", e);
            }
        } catch (Exception e) {
            logger.error("Report consumer failed", e);
        } finally {
            consumer.close();
            logger.info("Report consumer closed.");
        }
    }

    public void stop() {
        running = false;
        if (consumer != null) {
            consumer.wakeup();
        }
    }
}

 
