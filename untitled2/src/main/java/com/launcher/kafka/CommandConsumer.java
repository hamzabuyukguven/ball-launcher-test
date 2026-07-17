package com.launcher.kafka;

import com.launcher.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.launcher.kafka.model.LaunchCommand;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


import java.time.Duration;
import java.util.Properties;
import java.util.Collections;

public class CommandConsumer {
    public static final Logger logger = LoggerFactory.getLogger(CommandConsumer.class);
    private final KafkaConsumer<String, String> consumer;
    private final ObjectMapper objectMapper;

    public CommandConsumer(){
        this.objectMapper = new ObjectMapper();

        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "launcher-group");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");

        this.consumer = new KafkaConsumer<>(props);
    }

    public void startListening(){
        consumer.subscribe(Collections.singletonList("launcher.system.command"));
        logger.info("Listening on Kafka, Waiting for commands...");

        while (true) {
            ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
            for(ConsumerRecord<String, String> record : records){
                try {
                    LaunchCommand command = objectMapper.readValue(record.value(), LaunchCommand.class);

                    logger.info("New command! Action: " + command.getAction() + ", X: " + command.getTargetX() + ", Y: " + command.getTargetY());
                }catch (Exception e){
                    logger.warn(e.getMessage());
                }
            }
        }
    }





}
