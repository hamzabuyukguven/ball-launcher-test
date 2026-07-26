package com.hamza.balllauncherfrontend;

import com.hamza.balllauncherfrontend.kafka.CommandProducer;
import com.hamza.balllauncherfrontend.kafka.LaunchCommand;
import com.hamza.balllauncherfrontend.kafka.LauncherTelemetry;
import com.hamza.balllauncherfrontend.kafka.SystemStatusConsumer;
import com.hamza.balllauncherfrontend.kafka.SystemReportConsumer;
import com.hamza.balllauncherfrontend.kafka.LauncherAction;

import javafx.application.Platform;
import javafx.animation.PauseTransition;
import javafx.scene.control.ComboBox;
import javafx.util.Duration;
import javafx.beans.InvalidationListener;
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
    @FXML private ComboBox<String> ballTypeField;
    @FXML private Label connectionLabel;
    @FXML private Label readyLabel;
    @FXML private Canvas compassCanvas;
    @FXML private TextArea reportsArea;

    private CommandProducer producer;
    private SystemStatusConsumer consumer;
    private SystemReportConsumer reportConsumer;

    private double currentPlatformAngle = 0;
    private double currentCannonAngle = 90;

    @FXML
    public void initialize() {

        ballTypeField.getItems().addAll("A", "B", "C");
        ballTypeField.getSelectionModel().selectFirst();

        String kafkaBootstrapServers = AppConfig.getKafkaBootstrapServers();

        producer = new CommandProducer(kafkaBootstrapServers);
        logger.info("Kafka producer is ready.");

        consumer = new SystemStatusConsumer(kafkaBootstrapServers, "frontend-group", status -> {
            Platform.runLater(() -> {
                connectionLabel.setText(status.isConnected() ? "CONNECTED" : "DISCONNECTED");
                connectionLabel.setStyle(status.isConnected()
                        ? "-fx-background-color: #2ecc71; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;"
                        : "-fx-background-color: #e74c3c; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;");

                boolean ready = status.isReadyToFire();
                readyLabel.setText(ready ? "READY" : "NOT READY");
                readyLabel.setStyle(ready
                        ? "-fx-background-color: #2ecc71; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;"
                        : "-fx-background-color: #e74c3c; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;");

                currentPlatformAngle = status.getPlatformAngle();
                currentCannonAngle = status.getCannonAngle();
                drawCompass();

                ammunitionField.setText(String.valueOf(status.getAmmoCount()));

            });
        });

        compassCanvas.widthProperty().addListener((obs, oldVal, newVal) -> Platform.runLater(this::drawCompass));
        compassCanvas.heightProperty().addListener((obs, oldVal, newVal) -> Platform.runLater(this::drawCompass));

        Thread consumerThread = new Thread(consumer);
        consumerThread.setDaemon(true);
        consumerThread.start();

        reportConsumer = new SystemReportConsumer(kafkaBootstrapServers, "frontend-report-group", report -> {
            String message = report.getReportMessage();
            if (message != null && !message.isBlank()) {
                String line = String.format("[%s] %s", LocalTime.now().withNano(0), message);

                Platform.runLater(() -> reportsArea.appendText(line + System.lineSeparator()));
            }
        });

        Thread reportThread = new Thread(reportConsumer);
        reportThread.setDaemon(true);
        reportThread.start();

        Platform.runLater(this::drawCompass);
    }

    private void drawCompass() {
        GraphicsContext gc = compassCanvas.getGraphicsContext2D();
        double w = compassCanvas.getWidth();
        double h = compassCanvas.getHeight();
        double cx = w / 2;
        double cy = h / 2;
        double radius = Math.min(w, h) / 2 - 25;

        gc.clearRect(0, 0, w, h);

        gc.setFill(Color.web("#b0b0b0"));
        gc.fillOval(cx - radius, cy - radius, radius * 2, radius * 2);
        gc.setStroke(Color.BLACK);
        gc.setLineWidth(1.5);
        gc.strokeOval(cx - radius, cy - radius, radius * 2, radius * 2);

        gc.setLineWidth(1);
        for (int deg = 0; deg < 360; deg += 10) {
            double rad = Math.toRadians(deg - 90);
            double outerX = cx + radius * Math.cos(rad);
            double outerY = cy + radius * Math.sin(rad);
            double innerX = cx + (radius - 8) * Math.cos(rad);
            double innerY = cy + (radius - 8) * Math.sin(rad);
            gc.strokeLine(innerX, innerY, outerX, outerY);
        }

        gc.setFill(Color.BLACK);
        gc.setFont(javafx.scene.text.Font.font("Courier New", 13));
        gc.fillText("0°", cx - 6, cy - radius + 20);
        gc.fillText("90°", cx + radius - 30, cy + 5);
        gc.fillText("180°", cx - 13, cy + radius - 15);
        gc.fillText("270°", cx - radius + 10, cy + 5);

        Color needleColor = Color.web("#2b2b33");
        drawNeedle(gc, cx, cy, radius, currentPlatformAngle, needleColor);
        drawNeedle(gc, cx, cy, radius, currentCannonAngle, needleColor);
    }

    private void drawNeedle(GraphicsContext gc, double cx, double cy, double radius, double angleDegrees, Color color) {
        double rad = Math.toRadians(angleDegrees - 90);
        double x = cx + radius * 0.75 * Math.cos(rad);
        double y = cy + radius * 0.75 * Math.sin(rad);

        gc.setStroke(color);
        gc.setLineWidth(3);
        gc.strokeLine(cx, cy, x, y);

        double arrowLength = 12;
        double arrowAngle = Math.toRadians(25);
        double leftX = x - arrowLength * Math.cos(rad - arrowAngle);
        double leftY = y - arrowLength * Math.sin(rad - arrowAngle);
        double rightX = x - arrowLength * Math.cos(rad + arrowAngle);
        double rightY = y - arrowLength * Math.sin(rad + arrowAngle);

        gc.strokeLine(x, y, leftX, leftY);
        gc.strokeLine(x, y, rightX, rightY);
    }

    @FXML
    protected void onFireButtonClick() {
        if ("NOT READY".equals(readyLabel.getText())) {
            logger.warn("System is NOT READY. Fire command ignored.");
            return;
        }

        try {
            double x = Double.parseDouble(targetXField.getText());
            double y = Double.parseDouble(targetYField.getText());

            LauncherTelemetry telemetry = new LauncherTelemetry(x, y);

            producer.sendTelemetry(x, y);
            producer.sendCommand(new LaunchCommand(LauncherAction.FIRE, telemetry));

            logger.info("Telemetry and FIRE command sent for X:{} Y:{}", x, y);

            readyLabel.setText("NOT READY");
            readyLabel.setStyle("-fx-background-color: #e74c3c; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;");

            PauseTransition reloadTimer = new PauseTransition(Duration.seconds(3));

            reloadTimer.setOnFinished(event -> {
                if ("CONNECTED".equals(connectionLabel.getText())) {
                    readyLabel.setText("READY");
                    readyLabel.setStyle("-fx-background-color: #2ecc71; -fx-text-fill: white; -fx-padding: 8 20; -fx-font-weight: bold;");
                    logger.info("System is READY again.");
                }
            });

            reloadTimer.play();

        } catch (NumberFormatException e) {
            logger.warn("Invalid X or Y value entered.");
        }
    }

    @FXML
    protected void onStowButtonClick() {
        producer.sendCommand(new LaunchCommand(LauncherAction.STOW, null));
        logger.info("STOW command sent.");
    }

    @FXML
    protected void onEmergencyStopButtonClick() {
        producer.sendCommand(new LaunchCommand(LauncherAction.EMERGENCY_STOP, null));
        logger.warn("EMERGENCY STOP command sent!");
    }

    @FXML
    protected void onReportsButtonClick() {
        reportsArea.setVisible(!reportsArea.isVisible());
        logger.info("Reports panel toggled.");
    }
    @FXML
    protected void onSetTargetButtonClick() {
        try {
            double x = Double.parseDouble(targetXField.getText());
            double y = Double.parseDouble(targetYField.getText());

            LauncherTelemetry telemetry = new LauncherTelemetry(x, y);

            producer.sendTelemetry(x, y);
            producer.sendCommand(new LaunchCommand(LauncherAction.SET_MANUAL_TARGET, telemetry));

            logger.info("SET_MANUAL_TARGET command sent for X:{} Y:{}", x, y);
        } catch (NumberFormatException e) {
            logger.warn("Invalid X or Y value entered.");
        }
    }

    public void shutdown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.stop();
        if (reportConsumer != null) reportConsumer.stop();
        logger.info("Kafka connections closed safely.");
    }
}


