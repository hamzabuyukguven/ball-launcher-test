package com.launcher.kafka;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.launcher.kafka.model.SystemStatus;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.common.protocol.types.Field;
import org.apache.kafka.common.serialization.StringSerializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.Properties;

public class SystemStatusPublisher {

    private ObjectMapper objectMapper = new ObjectMapper();
    private static final Logger logger = LoggerFactory.getLogger(SystemStatusPublisher.class);
    private static final String STATUS_TOPIC = "launcher.system.status";
    private final KafkaProducer<String, String> producer;
    private String topicName;


    public SystemStatusPublisher() {
        this("172.20.10.3:9092");
    }


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


    private String serializeToJson(SystemStatus payload) {
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
        if (producer != null) {
            logger.info("Closing Kafka system status publisher.");
            producer.close();

        }
    }

    public void publishStatus(SystemStatus status) {
        try{
            String jsonStatus = objectMapper.writeValueAsString(status);
            ProducerRecord<String, String> record = new ProducerRecord<>(STATUS_TOPIC, jsonStatus);

            producer.send(record,(metadata, exception) -> {
                if (exception != null) {
                    logger.error("ERROR: Status info couldn't sent to UI",  exception);

                }else {
                    logger.debug("Sent status to UI: " + jsonStatus);
                }
            });

        }catch (Exception e){
            logger.error("ERROR: JSON serialization error.",  e);
        }

    }
}


