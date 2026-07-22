package com.hamza.balllauncherfrontend;

import com.hamza.balllauncherfrontend.kafka.CommandProducer;
import com.hamza.balllauncherfrontend.kafka.LaunchCommand;
import com.hamza.balllauncherfrontend.kafka.LauncherTelemetry;
import com.hamza.balllauncherfrontend.kafka.SystemStatusConsumer;
import com.hamza.balllauncherfrontend.kafka.SystemReportConsumer;

import javafx.application.Platform;
import javafx.fxml.FXML;
import javafx.scene.canvas.Canvas;
import javafx.scene.canvas.GraphicsContext;
import javafx.scene.control.Label;
import javafx.scene.control.TextArea;
import javafx.scene.control.TextField;
import javafx.scene.paint.Color;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalTime;

public class HelloController {

    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);

    @FXML private TextField targetXField;
    @FXML private TextField targetYField;
    @FXML private TextField ammunitionField;
    @FXML private TextField ballTypeField;
    @FXML private Label connectionLabel;
    @FXML private Label readyLabel;
    @FXML private Canvas compassCanvas;
    @FXML private TextArea reportsArea;

    private CommandProducer producer;
    private SystemStatusConsumer consumer;
    private SystemReportConsumer reportConsumer;

    private double currentPlatformAngle = 0;
    private double currentCannonAngle = 0;

    @FXML
    public void initialize() {
        String kafkaBootstrapServers = "192.168.1.109:9092"; // Backendci ile güncel adresi teyit et

        producer = new CommandProducer(kafkaBootstrapServers);
        logger.info("Kafka producer is ready.");

        consumer = new SystemStatusConsumer(kafkaBootstrapServers, "frontend-group", status -> {
            connectionLabel.setText(status.isConnected() ? "CONNECTED" : "DISCONNECTED");
            connectionLabel.setStyle(status.isConnected()
                ? "-fx-background-color: #2ecc71; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;"
                : "-fx-background-color: #e74c3c; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;");

            boolean ready = "READY".equalsIgnoreCase(status.getAvailability());
            readyLabel.setText(ready ? "READY" : "NOT READY");
            readyLabel.setStyle(ready
                ? "-fx-background-color: #2ecc71; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;"
                : "-fx-background-color: #e74c3c; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;");

            currentPlatformAngle = status.getPlatformAngle();
            currentCannonAngle = status.getCannonAngle();
            drawCompass();
        });

        Thread consumerThread = new Thread(consumer);
        consumerThread.setDaemon(true);
        consumerThread.start();

        reportConsumer = new SystemReportConsumer(kafkaBootstrapServers, "frontend-report-group", report -> {
            String line = String.format("[%s] %s", LocalTime.now().toString(), report.getReportMessage());
            reportsArea.appendText(line + "\n");
        });

        Thread reportThread = new Thread(reportConsumer);
        reportThread.setDaemon(true);
        reportThread.start();

        drawCompass();
    }

    private void drawCompass() {
        GraphicsContext gc = compassCanvas.getGraphicsContext2D();
        double w = compassCanvas.getWidth();
        double h = compassCanvas.getHeight();
        double cx = w / 2;
        double cy = h / 2;
        double radius = Math.min(w, h) / 2 - 10;

        gc.clearRect(0, 0, w, h);
        gc.setFill(Color.WHITESMOKE);
        gc.fillOval(cx - radius, cy - radius, radius * 2, radius * 2);
        gc.setStroke(Color.BLACK);
        gc.strokeOval(cx - radius, cy - radius, radius * 2, radius * 2);

        drawNeedle(gc, cx, cy, radius, currentPlatformAngle, Color.BLUE);
        drawNeedle(gc, cx, cy, radius, currentCannonAngle, Color.RED);
    }

    private void drawNeedle(GraphicsContext gc, double cx, double cy, double radius, double angleDegrees, Color color) {
        double rad = Math.toRadians(angleDegrees - 90);
        double x = cx + radius * 0.8 * Math.cos(rad);
        double y = cy + radius * 0.8 * Math.sin(rad);
        gc.setStroke(color);
        gc.setLineWidth(3);
        gc.strokeLine(cx, cy, x, y);
    }

    @FXML
    protected void onFireButtonClick() {
        try {
            double x = Double.parseDouble(targetXField.getText());
            double y = Double.parseDouble(targetYField.getText());

            LauncherTelemetry telemetry = new LauncherTelemetry(x, y);

            producer.sendTelemetry(x, y);
            producer.sendCommand(new LaunchCommand("FIRE", telemetry));

            logger.info("Telemetry and FIRE command sent for X:{} Y:{}", x, y);
        } catch (NumberFormatException e) {
            logger.warn("Invalid X or Y value entered.");
        }
    }

    @FXML
    protected void onStowButtonClick() {
        producer.sendCommand(new LaunchCommand("STOW", null));
        logger.info("STOW command sent.");
    }

    @FXML
    protected void onEmergencyStopButtonClick() {
        producer.sendCommand(new LaunchCommand("EMERGENCY_STOP", null));
        logger.warn("EMERGENCY STOP command sent!");
    }

    @FXML
    protected void onReportsButtonClick() {
        logger.info("Reports panel toggled (already visible at bottom).");
    }

    public void shutdown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.stop();
        if (reportConsumer != null) reportConsumer.stop();
        logger.info("Kafka connections closed safely.");
    }
}
