package kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;

public class CommandProducer {

    private static final Logger logger = LoggerFactory.getLogger(CommandProducer.class);
    private static final String CMD_TOPIC = "launcher.system.command";

    private final KafkaProducer<String, String> producer;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public CommandProducer(String bootstrapServers) {
        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());

        this.producer = new KafkaProducer<>(props);
    }

    public void sendCommand(LaunchCommand command) {
        try {
            String jsonCommand = objectMapper.writeValueAsString(command);
            ProducerRecord<String, String> record = new ProducerRecord<>(CMD_TOPIC, jsonCommand);

            producer.send(record, (metadata, exception) -> {
                if (exception != null) {
                    logger.error("ERROR: Failed to send command! ", exception);
                } else {
                    logger.info("SUCCESS: Command sent -> {}", jsonCommand);
                }
            });
        } catch (Exception e) {
            logger.error("Error serializing or sending command: ", e);
        }
    }

    public void close() {
        if (producer != null) {
            producer.close();
            logger.info("Producer closed.");
        }
    }
}
