package com.launcher.kafka;

import com.launcher.kafka.model.SystemStatus;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.Properties;

public class SystemStatusPublisher {

    private static final Logger logger = LoggerFactory.getLogger(SystemStatusPublisher.class);

    private final KafkaProducer<String, String> producer;
    private final String topicName;

    public SystemStatusPublisher(String bootStrapServers) {
        this.topicName = "launcher.system.status";


        Properties props = new Properties();

        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootStrapServers);

        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());

        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.RETRIES_CONFIG, 3);

        this.producer = new KafkaProducer<>(props);
        logger.info("Kafka system status publisher successfully initialized.");
    }


    public void evaluateAndPublish(boolean isConnected, String availability, double platformAngle, double cannonAngle) {

        SystemStatus status = new SystemStatus(isConnected, availability, platformAngle, cannonAngle);

        String jsonPayload = serializeToJson(status);

        ProducerRecord<String, String> record = new ProducerRecord<>(topicName,"system_status_key", jsonPayload);

        producer.send(record, (metadata, exception) -> {
            if (exception != null) {
                logger.error("Failed to publish system status.",  exception);

            }
            else  {
                logger.debug("Published system status. Partition: {}, Offset: {}",  metadata.partition(), metadata.offset());
            }
        });

    }
    private String serializeToJson(SystemStatus payload){
        return String.format(
                "{\"connected\":%b,\"availability\":\"%s\",\"platformAngle\":%.2f,\"cannonAngle\":%.2f,\"timestamp\":%d}",
                payload.isConnected(),
                payload.getAvailability(),
                payload.getPlatformAngle(),
                payload.getCannonAngle(),
                payload.getTimeStamp()
        );

    }

    public void close() {
        if(producer != null) {
            logger.info("Closing Kafka system status publisher.");
            producer.close();

        }
    }
}
