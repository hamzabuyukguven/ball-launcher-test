package com.hamza.balllauncherfrontend;

import com.hamza.balllauncherfrontend.kafka.CommandProducer;
import com.hamza.balllauncherfrontend.kafka.LaunchCommand;
import com.hamza.balllauncherfrontend.kafka.SystemStatusConsumer;

import javafx.fxml.FXML;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class HelloController {

    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);

    private CommandProducer producer;
    private SystemStatusConsumer consumer;

    @FXML
    public void initialize() {
        String kafkaBootstrapServers = "10.152.220.16:9092";

        producer = new CommandProducer(kafkaBootstrapServers);
        logger.info("Kafka producer is ready.");

        consumer = new SystemStatusConsumer(kafkaBootstrapServers, "launcher-group", status -> {
            logger.info("Status received -> Connected: {}, Availability: {}, PlatformAngle: {}, CannonAngle: {}",
                    status.isConnected(), status.getAvailability(), status.getPlatformAngle(), status.getCannonAngle());
        });

        Thread consumerThread = new Thread(consumer);
        consumerThread.setDaemon(true);
        consumerThread.start();
    }

    public void fire(double x, double y) {
        LaunchCommand cmd = new LaunchCommand("FIRE", x, y);
        producer.sendCommand(cmd);
        logger.info("FIRE command sent for X:{} Y:{}", x, y);
    }

    public void emergencyStop() {
        LaunchCommand cmd = new LaunchCommand("EMERGENCY_STOP", 0.0, 0.0);
        producer.sendCommand(cmd);
        logger.warn("EMERGENCY STOP command sent!");
    }

    public void shutdown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.stop();
        logger.info("Kafka connections closed safely.");
    }

    @FXML
    protected void onHelloButtonClick(){
        logger.info("Hello button clicked(test button");
    }
}
