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
import javafx.fxml.FXML;
import javafx.scene.canvas.Canvas;
import javafx.scene.canvas.GraphicsContext;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.TextArea;
import javafx.scene.control.TextField;
import javafx.scene.paint.Color;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalTime;

public class HelloController {

    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);

    @FXML private Label connectionLabel;
    @FXML private Label readyLabel;

    @FXML private Label availabilityLabel;
    @FXML private Label coordinatesLabel;
    @FXML private Label panLabel;
    @FXML private Label tiltLabel;
    @FXML private Label ammoLabel;
    @FXML private Label aimLabel;
    @FXML private Label statusMessageLabel;

    @FXML private TextField targetXField;
    @FXML private TextField targetYField;
    @FXML private TextField targetZField;
    @FXML private ComboBox<String> ballTypeField;
    @FXML private TextArea reportsArea;
    @FXML private Canvas compassCanvas;
    @FXML private Button fireButton;

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
        logger.info("Kafka producer is ready on: {}", kafkaBootstrapServers);

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


                if (availabilityLabel != null) availabilityLabel.setText(status.getAvailability() != null ? status.getAvailability() : "UNKNOWN");
                if (coordinatesLabel != null) coordinatesLabel.setText(String.format("X: %.2f m Y: %.2f m", status.getXCoordinate(), status.getYCoordinate()));
                if (panLabel != null) panLabel.setText(String.format("Pan: %.2f°", status.getPlatformAngle()));
                if (tiltLabel != null) tiltLabel.setText(String.format("Tilt: %.2f°", status.getCannonAngle()));
                if (ammoLabel != null) ammoLabel.setText(String.format("%d", status.getAmmoCount()));

                if (aimLabel != null) {
                    aimLabel.setText(status.isAimed() ? "ALIGNED" : "ALIGNING");
                    aimLabel.setTextFill(status.isAimed() ? Color.FORESTGREEN : Color.DARKORANGE);
                }

                if (fireButton != null) {
                    fireButton.setDisable(!status.isConnected());
                }

                currentPlatformAngle = status.getPlatformAngle();
                currentCannonAngle = status.getCannonAngle();
                drawCompass();
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
                Platform.runLater(() -> {
                    reportsArea.appendText(line + System.lineSeparator());
                    trimReportsIfNeeded();
                    reportsArea.setScrollTop(Double.MAX_VALUE);
                });
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

        gc.setFill(Color.rgb(0, 0, 0, 0.25));
        gc.fillOval(cx - radius + 3, cy - radius + 4, radius * 2, radius * 2);

        gc.setFill(Color.web("#c4c6ca"));
        gc.fillOval(cx - radius, cy - radius, radius * 2, radius * 2);
        gc.setFill(Color.web("#d8dadd"));
        gc.fillOval(cx - radius + 4, cy - radius + 4, radius * 2 - 8, radius * 2 - 8);

        gc.setStroke(Color.web("#1a1a1a"));
        gc.setLineWidth(2);
        gc.strokeOval(cx - radius, cy - radius, radius * 2, radius * 2);

        for (int deg = 0; deg < 360; deg += 10) {
            double rad = Math.toRadians(deg - 90);
            boolean major = deg % 30 == 0;
            double tickLength = major ? 12 : 6;
            gc.setLineWidth(major ? 1.8 : 1);
            gc.setStroke(Color.web("#1a1a1a"));

            double outerX = cx + radius * Math.cos(rad);
            double outerY = cy + radius * Math.sin(rad);
            double innerX = cx + (radius - tickLength) * Math.cos(rad);
            double innerY = cy + (radius - tickLength) * Math.sin(rad);
            gc.strokeLine(innerX, innerY, outerX, outerY);
        }

        drawNeedle(gc, cx, cy, radius, currentPlatformAngle, Color.web("#2b2b33"), 4);
        drawNeedle(gc, cx, cy, radius, currentCannonAngle, Color.web("#c0392b"), 3);

        gc.setFont(javafx.scene.text.Font.font("Courier New", javafx.scene.text.FontWeight.BOLD, 13));
        drawLabelWithBackground(gc, "0°", cx - 8, cy - radius + 22);
        drawLabelWithBackground(gc, "90°", cx + radius - 36, cy + 5);
        drawLabelWithBackground(gc, "180°", cx - 16, cy + radius - 10);
        drawLabelWithBackground(gc, "270°", cx - radius + 6, cy + 5);

        gc.setFill(Color.web("#1a1a1a"));
        gc.fillOval(cx - 5, cy - 5, 10, 10);
        gc.setFill(Color.web("#e07856"));
        gc.fillOval(cx - 2.5, cy - 2.5, 5, 5);
    }

    private void drawLabelWithBackground(GraphicsContext gc, String text, double x, double y) {
        double padding = 3;
        double textWidth = text.length() * 8;
        gc.setFill(Color.rgb(216, 218, 221, 0.9));
        gc.fillRect(x - padding, y - 12, textWidth + padding * 2, 16);
        gc.setFill(Color.web("#1a1a1a"));
        gc.fillText(text, x, y);
    }

    private void drawNeedle(GraphicsContext gc, double cx, double cy, double radius, double angleDegrees, Color color, double lineWidth) {
        double rad = Math.toRadians(angleDegrees - 90);
        double x = cx + radius * 0.68 * Math.cos(rad);
        double y = cy + radius * 0.68 * Math.sin(rad);

        gc.setStroke(color);
        gc.setLineWidth(lineWidth);
        gc.strokeLine(cx, cy, x, y);

        double arrowLength = 12;
        double arrowAngle = Math.toRadians(22);
        double leftX = x - arrowLength * Math.cos(rad - arrowAngle);
        double leftY = y - arrowLength * Math.sin(rad - arrowAngle);
        double rightX = x - arrowLength * Math.cos(rad + arrowAngle);
        double rightY = y - arrowLength * Math.sin(rad + arrowAngle);

        gc.setLineWidth(lineWidth * 0.8);
        gc.strokeLine(x, y, leftX, leftY);
        gc.strokeLine(x, y, rightX, rightY);
    }

    private void trimReportsIfNeeded() {
        String[] lines = reportsArea.getText().split("\n");
        int maxLines = AppConfig.getReportsMaxLines();
        if (lines.length > maxLines) {
            StringBuilder trimmed = new StringBuilder();
            for (int i = lines.length - maxLines; i < lines.length; i++) {
                trimmed.append(lines[i]).append("\n");
            }
            reportsArea.setText(trimmed.toString());
        }
    }

    @FXML
    protected void onFireButtonClick() {
        if ("NOT READY".equals(readyLabel.getText())) {
            logger.warn("System is NOT READY. Fire command ignored.");
            setUiMessage("System is not ready to fire!", true);
            return;
        }

        try {
            double x = Double.parseDouble(targetXField.getText());
            double y = Double.parseDouble(targetYField.getText());

            LauncherTelemetry telemetry = new LauncherTelemetry(x, y);

            producer.sendTelemetry(x, y);
            producer.sendCommand(new LaunchCommand(LauncherAction.FIRE, telemetry));

            logger.info("Telemetry and FIRE command sent for X:{} Y:{}", x, y);
            setUiMessage("Fire command queued successfully.", false);

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
            setUiMessage("Invalid coordinates entered!", true);
        }
    }

    @FXML
    protected void onStowButtonClick() {
        producer.sendCommand(new LaunchCommand(LauncherAction.STOW, null));
        logger.info("STOW command sent.");
        setUiMessage("Stow command sent.", false);
    }

    @FXML
    protected void onEmergencyStopButtonClick() {
        producer.sendCommand(new LaunchCommand(LauncherAction.EMERGENCY_STOP, null));
        logger.warn("EMERGENCY STOP command sent!");
        setUiMessage("EMERGENCY STOP ENGAGED!", true);
    }
@FXML
    protected void onClearEmergencyStop() {
        producer.sendCommand(new LaunchCommand(LauncherAction.EMERGENCY_STOP, null));
        logger.info("Emergency stop clear command sent.");
        setUiMessage("Emergency stop cleared.", false);
    }

    @FXML
    protected void onUseTrackedTarget() {
        producer.sendCommand(new LaunchCommand(LauncherAction.USE_TRACKED_TARGET, null));
        logger.info("Simulation target stream selected.");
        setUiMessage("Using tracked simulation targets.", false);
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
            setUiMessage("Target manually set.", false);
        } catch (NumberFormatException e) {
            logger.warn("Invalid X or Y value entered.");
            setUiMessage("Invalid coordinates entered!", true);
        }
    }

    private void setUiMessage(String message, boolean isError) {
        if (statusMessageLabel != null) {
            Platform.runLater(() -> {
                statusMessageLabel.setText(message);
                statusMessageLabel.setTextFill(isError ? Color.FIREBRICK : Color.DARKSLATEGRAY);
            });
        }
    }

    public void shutdown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.stop();
        if (reportConsumer != null) reportConsumer.stop();
        logger.info("Kafka connections closed safely.");
    }
}

