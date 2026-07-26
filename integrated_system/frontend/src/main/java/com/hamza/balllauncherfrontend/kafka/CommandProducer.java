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
import java.util.concurrent.CompletableFuture;

public class CommandProducer implements AutoCloseable {
    private static final Logger logger = LoggerFactory.getLogger(CommandProducer.class);

    private final KafkaProducer<String, String> producer;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String commandTopic;

    public CommandProducer() {
        this.commandTopic = AppConfig.commandTopic();

        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, AppConfig.kafkaBootstrapServers());
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        props.put(ProducerConfig.RETRIES_CONFIG, Integer.MAX_VALUE);
        props.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, 10_000);
        props.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG, 3_000);
        props.put(ProducerConfig.CLIENT_ID_CONFIG, "launcher-frontend-command-producer");
        producer = new KafkaProducer<>(props);
    }

    public CompletableFuture<Void> send(LauncherAction action, LauncherTelemetry telemetry) {
        CompletableFuture<Void> result = new CompletableFuture<>();
        try {
            String json = objectMapper.writeValueAsString(new LaunchCommand(action, telemetry));
            producer.send(new ProducerRecord<>(commandTopic, json), (metadata, error) -> {
                if (error != null) {
                    logger.error("Command publish failed: {}", action, error);
                    result.completeExceptionally(error);
                } else {
                    logger.info("Command {} published to {} partition={} offset={}",
                            action, metadata.topic(), metadata.partition(), metadata.offset());
                    result.complete(null);
                }
            });
        } catch (Exception e) {
            result.completeExceptionally(e);
        }
        return result;
    }

    @Override
    public void close() {
        producer.flush();
        producer.close();
    }
}
