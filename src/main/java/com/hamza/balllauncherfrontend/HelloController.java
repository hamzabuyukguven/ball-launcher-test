package com.hamza.balllauncherfrontend;

import com.hamza.balllauncherfrontend.kafka.CommandProducer;
import com.hamza.balllauncherfrontend.kafka.LaunchCommand;
import com.hamza.balllauncherfrontend.kafka.SystemStatusConsumer;

import javafx.fxml.FXML;
import javafx.scene.control.Label;
import javafx.scene.control.TextField;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class HelloController {

    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);

    @FXML
    private TextField targetXField;

    @FXML
    private TextField targetYField;

    @FXML
    private Label statusLabel;

    private CommandProducer producer;
    private SystemStatusConsumer consumer;

    @FXML
    public void initialize() {
        String kafkaBootstrapServers = "192.168.1.109:9092";

        producer = new CommandProducer(kafkaBootstrapServers);
        logger.info("Kafka producer is ready.");

        consumer = new SystemStatusConsumer(kafkaBootstrapServers, "frontend-group", status -> {
            statusLabel.setText(String.format("Connected: %b | Availability: %s | Platform: %.1f | Cannon: %.1f",
                status.isConnected(), status.getAvailability(), status.getPlatformAngle(), status.getCannonAngle()));
        });

        Thread consumerThread = new Thread(consumer);
        consumerThread.setDaemon(true);
        consumerThread.start();
    }

    @FXML
    protected void onFireButtonClick() {
        try {
            double x = Double.parseDouble(targetXField.getText());
            double y = Double.parseDouble(targetYField.getText());

            producer.sendTelemetry(x, y);
            producer.sendCommand(new LaunchCommand("FIRE"));

            logger.info("Telemetry and FIRE command sent for X:{} Y:{}", x, y);
        } catch (NumberFormatException e) {
            logger.warn("Invalid X or Y value entered.");
        }
    }

    @FXML
    protected void onStowButtonClick() {
        producer.sendCommand(new LaunchCommand("STOW"));
        logger.info("STOW command sent.");
    }

    @FXML
    protected void onEmergencyStopButtonClick() {
        producer.sendCommand(new LaunchCommand("EMERGENCY_STOP"));
        logger.warn("EMERGENCY STOP command sent!");
    }

    public void shutdown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.stop();
        logger.info("Kafka connections closed safely.");
    }
}
