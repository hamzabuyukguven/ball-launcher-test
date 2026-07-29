package com.hamza.balllauncherfrontend;

import com.hamza.balllauncherfrontend.kafka.CommandProducer;
import com.hamza.balllauncherfrontend.kafka.LaunchCommand;
import com.hamza.balllauncherfrontend.kafka.LauncherAction;
import com.hamza.balllauncherfrontend.kafka.LauncherTelemetry;
import com.hamza.balllauncherfrontend.kafka.SystemReportConsumer;
import com.hamza.balllauncherfrontend.kafka.SystemStatusConsumer;

import javafx.animation.PauseTransition;
import javafx.application.Platform;
import javafx.fxml.FXML;
import javafx.scene.canvas.Canvas;
import javafx.scene.canvas.GraphicsContext;
import javafx.scene.control.Button;
import javafx.scene.control.ComboBox;
import javafx.scene.control.Label;
import javafx.scene.control.TextArea;
import javafx.scene.control.TextField;
import javafx.scene.control.ToggleButton;
import javafx.scene.control.ToggleGroup;
import javafx.scene.layout.HBox;
import javafx.scene.paint.Color;
import javafx.scene.shape.ArcType;
import javafx.scene.text.Font;
import javafx.scene.text.FontWeight;
import javafx.util.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalTime;

public class HelloController {

    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);

    private static final double METERS_PER_KNOT_UNIT = 1852.0;

    private static final Color OWNSHIP_COLOR = Color.web("#1f3d5c");
    private static final Color BEARING_COLOR = Color.web("#c0392b");
    private static final Color ELEVATION_COLOR = Color.web("#d98324");
    private static final Color FACE_OUTER = Color.web("#c4c6ca");
    private static final Color FACE_INNER = Color.web("#d8dadd");
    private static final Color INK = Color.web("#1a1a1a");

    private static final String PILL_OK = "-fx-background-color: #2ecc71; -fx-text-fill: white; -fx-padding: 4 14; -fx-background-radius: 4; -fx-font-weight: bold;";
    private static final String PILL_BAD = "-fx-background-color: #e74c3c; -fx-text-fill: white; -fx-padding: 4 14; -fx-background-radius: 4; -fx-font-weight: bold;";
    private static final String PILL_NEUTRAL = "-fx-background-color: #6b7280; -fx-text-fill: white; -fx-padding: 4 14; -fx-background-radius: 4; -fx-font-weight: bold;";
    private static final String PILL_ORANGE = "-fx-background-color: #d98324; -fx-text-fill: white; -fx-padding: 4 14; -fx-background-radius: 4; -fx-font-weight: bold;";
    private static final String PILL_BLUE = "-fx-background-color: #4a8cd2; -fx-text-fill: white; -fx-padding: 4 14; -fx-background-radius: 4; -fx-font-weight: bold;";
    private static final String PILL_HEADER_OK = "-fx-background-color: #2ecc71; -fx-text-fill: white; -fx-padding: 6 16; -fx-background-radius: 4; -fx-font-weight: bold;";
    private static final String PILL_HEADER_BAD = "-fx-background-color: #e74c3c; -fx-text-fill: white; -fx-padding: 6 16; -fx-background-radius: 4; -fx-font-weight: bold;";

    private static final String HEADER_NORMAL = "-fx-background-color: #18324a; -fx-padding: 16;";
    private static final String HEADER_EMERGENCY = "-fx-background-color: #7e1111; -fx-padding: 16;";

    private static final String STOW_ACTIVE = "-fx-background-color: #4a8cd2; -fx-text-fill: white; -fx-font-weight: bold; -fx-font-size: 15px; -fx-padding: 12; -fx-background-radius: 4;";
    private static final String STOW_BUSY = "-fx-background-color: #9dbde0; -fx-text-fill: #2c4a68; -fx-font-weight: bold; -fx-font-size: 15px; -fx-padding: 12; -fx-background-radius: 4;";

    @FXML private HBox headerBar;
    @FXML private Label emergencyBanner;
    @FXML private Label connectionLabel;
    @FXML private Label readyLabel;
    @FXML private Label availabilityLabel;
    @FXML private Label aimLabel;
    @FXML private Label coordinatesLabel;
    @FXML private Label headingLabel;
    @FXML private Label panLabel;
    @FXML private Label tiltLabel;
    @FXML private Label ammoLabel;
    @FXML private Label statusMessageLabel;

    @FXML private TextField targetXField;
    @FXML private TextField targetYField;
    @FXML private ComboBox<String> ballTypeField;
    @FXML private TextArea reportsArea;
    @FXML private Canvas compassCanvas;
    @FXML private Canvas elevationCanvas;
    @FXML private Button fireButton;
    @FXML private Button autoFireButton;
    @FXML private Button stowButton;
    @FXML private Button emergencyButton;
    @FXML private ToggleButton unitMeterToggle;
    @FXML private ToggleButton unitKnotToggle;

    private CommandProducer producer;
    private SystemStatusConsumer consumer;
    private SystemReportConsumer reportConsumer;

    private double ownshipHeading = 0;
    private double gunBearing = 0;
    private double gunElevation = 0;
    private double lastX = 0;
    private double lastY = 0;

    private boolean emergencyActive = false;
    private boolean stowInProgress = false;
    private boolean connected = false;
    private boolean readyToFire = false;
    private boolean aimed = false;

    private PauseTransition stowTimeout;

    @FXML
    public void initialize() {
        ballTypeField.getItems().addAll("76MM");
        ballTypeField.getSelectionModel().selectFirst();

        reportsArea.managedProperty().bind(reportsArea.visibleProperty());

        ToggleGroup unitGroup = new ToggleGroup();
        unitMeterToggle.setToggleGroup(unitGroup);
        unitKnotToggle.setToggleGroup(unitGroup);
        unitGroup.selectedToggleProperty().addListener((obs, old, sel) -> {
            if (sel == null) {
                old.setSelected(true);
            } else {
                updateCoordinatesLabel();
            }
        });

        stowTimeout = new PauseTransition(Duration.seconds(10));
        stowTimeout.setOnFinished(e -> finishStow());

        String servers = AppConfig.getKafkaBootstrapServers();
        producer = new CommandProducer(servers);
        logger.info("Kafka producer is ready on: {}", servers);

        consumer = new SystemStatusConsumer(servers, AppConfig.statusGroupId(), status -> Platform.runLater(() -> {
            connected = status.isConnected();
            readyToFire = status.isReadyToFire();
            aimed = status.isAimed();

            connectionLabel.setText(connected ? "CONNECTED" : "DISCONNECTED");
            connectionLabel.setStyle(connected ? PILL_HEADER_OK : PILL_HEADER_BAD);

            String availability = status.getAvailability() != null
                    ? status.getAvailability().toUpperCase()
                    : "UNKNOWN";
            availabilityLabel.setText(availability);
            availabilityLabel.setStyle(availabilityStyle(availability));

            aimLabel.setText(aimed ? "ALIGNED" : "ALIGNING");
            aimLabel.setStyle(aimed ? PILL_OK : PILL_ORANGE);

            lastX = status.getXCoordinate();
            lastY = status.getYCoordinate();
            updateCoordinatesLabel();

            ownshipHeading = status.getPlatformAngle();
            gunBearing = status.getCannonAngle();
            gunElevation = status.getElevationAngle();

            headingLabel.setText(String.format("Ownship: %.2f°", ownshipHeading));
            panLabel.setText(String.format("Bearing: %.2f°", gunBearing));
            tiltLabel.setText(String.format("Elev: %.2f°", gunElevation));
            ammoLabel.setText(String.valueOf(status.getAmmoCount()));

            drawCompass();
            drawElevationGauge();

            if (stowInProgress && availability.contains("STOW")) {
                finishStow();
            }

            refreshFireState();
        }));

        reportConsumer = new SystemReportConsumer(servers, AppConfig.reportsGroupId(), report -> {
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

        compassCanvas.widthProperty().addListener((o, a, b) -> Platform.runLater(this::drawCompass));
        compassCanvas.heightProperty().addListener((o, a, b) -> Platform.runLater(this::drawCompass));
        elevationCanvas.widthProperty().addListener((o, a, b) -> Platform.runLater(this::drawElevationGauge));
        elevationCanvas.heightProperty().addListener((o, a, b) -> Platform.runLater(this::drawElevationGauge));

        startDaemon(consumer, "status-consumer");
        startDaemon(reportConsumer, "report-consumer");

        Platform.runLater(() -> {
            drawCompass();
            drawElevationGauge();
        });
        setUiMessage("Waiting for backend status...", false);
    }

    private void startDaemon(Runnable task, String name) {
        Thread t = new Thread(task, name);
        t.setDaemon(true);
        t.start();
    }

    private void updateCoordinatesLabel() {
        boolean meters = unitMeterToggle.isSelected();
        double x = meters ? lastX : lastX / METERS_PER_KNOT_UNIT;
        double y = meters ? lastY : lastY / METERS_PER_KNOT_UNIT;
        String unit = meters ? "m" : "kn";
        coordinatesLabel.setText(String.format("Ownship X: %.2f %s Y: %.2f %s", x, unit, y, unit));
    }

    private String availabilityStyle(String availability) {
        if (availability.contains("READY") || availability.contains("IDLE")) return PILL_OK;
        if (availability.contains("FAULT") || availability.contains("ERROR") || availability.contains("STOP")) return PILL_BAD;
        if (availability.contains("STOW") || availability.contains("BUSY") || availability.contains("MOVING")) return PILL_BLUE;
        if (availability.contains("UNKNOWN") || availability.isBlank()) return PILL_NEUTRAL;
        return PILL_ORANGE;
    }

    private void refreshFireState() {
        fireButton.setDisable(!(connected && readyToFire && !emergencyActive));
        autoFireButton.setDisable(!(connected && aimed && !emergencyActive));
        stowButton.setDisable(emergencyActive || stowInProgress);

        if (emergencyActive) {
            readyLabel.setText("E-STOP");
            readyLabel.setStyle(PILL_BAD);
        } else {
            readyLabel.setText(readyToFire ? "READY" : "NOT READY");
            readyLabel.setStyle(readyToFire ? PILL_OK : PILL_BAD);
        }
    }

    private void engageEmergency() {
        emergencyActive = true;
        emergencyBanner.setVisible(true);
        emergencyBanner.setManaged(true);
        headerBar.setStyle(HEADER_EMERGENCY);
        emergencyButton.setText("EMERGENCY STOP ENGAGED");
        finishStow();
        refreshFireState();
    }

    private boolean releaseEmergencyIfNeeded() {
        if (!emergencyActive) {
            return false;
        }
        producer.sendCommand(new LaunchCommand(LauncherAction.CLEAR_EMERGENCY_STOP, null));
        emergencyActive = false;
        emergencyBanner.setVisible(false);
        emergencyBanner.setManaged(false);
        headerBar.setStyle(HEADER_NORMAL);
        emergencyButton.setText("EMERGENCY STOP");
        refreshFireState();
        logger.info("Emergency stop auto-cleared by new command.");
        return true;
    }

    private void beginStow() {
        stowInProgress = true;
        stowButton.setText("STOWING...");
        stowButton.setStyle(STOW_BUSY);
        stowButton.setDisable(true);
        stowTimeout.playFromStart();
    }

    private void finishStow() {
        if (!stowInProgress) {
            return;
        }
        stowTimeout.stop();
        stowInProgress = false;
        stowButton.setText("STOW");
        stowButton.setStyle(STOW_ACTIVE);
        stowButton.setDisable(emergencyActive);
    }

    @FXML
    protected void onSetTargetButtonClick() {
        boolean released = releaseEmergencyIfNeeded();
        try {
            LauncherTelemetry telemetry = readTelemetry();
            producer.sendTelemetry(telemetry.getTargetX(), telemetry.getTargetY());
            producer.sendCommand(new LaunchCommand(LauncherAction.SET_MANUAL_TARGET, telemetry));
            logger.info("SET_MANUAL_TARGET sent X:{} Y:{}", telemetry.getTargetX(), telemetry.getTargetY());
            setUiMessage(released ? "Emergency released. Manual target set." : "Manual target set.", false);
        } catch (NumberFormatException e) {
            setUiMessage("Invalid coordinates entered.", true);
        }
    }

    @FXML
    protected void onUseTrackedTarget() {
        boolean released = releaseEmergencyIfNeeded();
        producer.sendCommand(new LaunchCommand(LauncherAction.USE_TRACKED_TARGET, null));
        setUiMessage(released ? "Emergency released. Tracker engaged." : "Tracker engaged. Waiting for alignment.", false);
    }

    @FXML
    protected void onAutoFireButtonClick() {
        boolean released = releaseEmergencyIfNeeded();
        if (!aimed) {
            setUiMessage("Tracker is not aligned yet.", true);
            return;
        }
        producer.sendCommand(new LaunchCommand(LauncherAction.FIRE, null));
        logger.info("FIRE sent on tracked target.");
        setUiMessage(released ? "Emergency released. Fire request sent on track." : "Fire request sent on tracked target.", false);
    }

    @FXML
    protected void onFireButtonClick() {
        boolean released = releaseEmergencyIfNeeded();
        if (!readyToFire) {
            setUiMessage("System is not ready to fire.", true);
            return;
        }
        try {
            LauncherTelemetry telemetry = readTelemetry();
            producer.sendTelemetry(telemetry.getTargetX(), telemetry.getTargetY());
            producer.sendCommand(new LaunchCommand(LauncherAction.FIRE, telemetry));
            logger.info("FIRE sent X:{} Y:{}", telemetry.getTargetX(), telemetry.getTargetY());
            setUiMessage(released ? "Emergency released. Fire request sent." : "Fire request sent.", false);
        } catch (NumberFormatException e) {
            setUiMessage("Invalid coordinates entered.", true);
        }
    }

    @FXML
    protected void onStowButtonClick() {
        boolean released = releaseEmergencyIfNeeded();
        producer.sendCommand(new LaunchCommand(LauncherAction.STOW, null));
        beginStow();
        setUiMessage(released ? "Emergency released. Stowing..." : "Stowing...", false);
    }

    @FXML
    protected void onEmergencyStopButtonClick() {
        producer.sendCommand(new LaunchCommand(LauncherAction.EMERGENCY_STOP, null));
        engageEmergency();
        logger.warn("EMERGENCY STOP command sent.");
        setUiMessage("EMERGENCY STOP engaged. Send any command to release.", true);
    }

    @FXML
    protected void onReportsButtonClick() {
        reportsArea.setVisible(!reportsArea.isVisible());
    }

    @FXML
    protected void onHelpButtonClick() {
        setUiMessage("Help panel is not implemented yet.", false);
    }

    private LauncherTelemetry readTelemetry() {
        double x = Double.parseDouble(targetXField.getText().trim());
        double y = Double.parseDouble(targetYField.getText().trim());
        return new LauncherTelemetry(x, y);
    }

    private void setUiMessage(String message, boolean isError) {
        statusMessageLabel.setText(message);
        statusMessageLabel.setTextFill(isError ? Color.web("#ff8a8a") : Color.web("#c3c9d4"));
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

    private void drawCompass() {
        GraphicsContext gc = compassCanvas.getGraphicsContext2D();
        double w = compassCanvas.getWidth();
        double h = compassCanvas.getHeight();
        double cx = w / 2;
        double cy = h / 2;
        double radius = Math.min(w, h) / 2 - 22;

        gc.clearRect(0, 0, w, h);

        gc.setFill(Color.rgb(0, 0, 0, 0.25));
        gc.fillOval(cx - radius + 3, cy - radius + 4, radius * 2, radius * 2);

        gc.setFill(FACE_OUTER);
        gc.fillOval(cx - radius, cy - radius, radius * 2, radius * 2);
        gc.setFill(FACE_INNER);
        gc.fillOval(cx - radius + 4, cy - radius + 4, radius * 2 - 8, radius * 2 - 8);

        gc.setStroke(INK);
        gc.setLineWidth(2);
        gc.strokeOval(cx - radius, cy - radius, radius * 2, radius * 2);

        for (int deg = 0; deg < 360; deg += 10) {
            double rad = Math.toRadians(deg - 90);
            boolean major = deg % 30 == 0;
            double tick = major ? 11 : 5;
            gc.setLineWidth(major ? 1.8 : 1);
            gc.setStroke(INK);
            gc.strokeLine(cx + (radius - tick) * Math.cos(rad), cy + (radius - tick) * Math.sin(rad),
                    cx + radius * Math.cos(rad), cy + radius * Math.sin(rad));
        }

        drawNeedle(gc, cx, cy, radius * 0.58, ownshipHeading, OWNSHIP_COLOR, 6);
        drawNeedle(gc, cx, cy, radius * 0.80, gunBearing, BEARING_COLOR, 2.2);

        gc.setFont(Font.font("Courier New", FontWeight.BOLD, 12));
        drawLabelWithBackground(gc, "0", cx - 4, cy - radius + 20);
        drawLabelWithBackground(gc, "90", cx + radius - 26, cy + 4);
        drawLabelWithBackground(gc, "180", cx - 11, cy + radius - 9);
        drawLabelWithBackground(gc, "270", cx - radius + 6, cy + 4);

        gc.setFill(INK);
        gc.fillOval(cx - 5, cy - 5, 10, 10);
        gc.setFill(Color.web("#e07856"));
        gc.fillOval(cx - 2.5, cy - 2.5, 5, 5);
    }

    private void drawElevationGauge() {
        GraphicsContext gc = elevationCanvas.getGraphicsContext2D();
        double w = elevationCanvas.getWidth();
        double h = elevationCanvas.getHeight();
        double px = 26;
        double py = h - 40;
        double radius = Math.min(w - 42, py - 30);

        gc.clearRect(0, 0, w, h);

        gc.setFill(Color.rgb(0, 0, 0, 0.25));
        gc.fillArc(px - radius + 2, py - radius + 3, radius * 2, radius * 2, 0, 90, ArcType.ROUND);

        gc.setFill(FACE_OUTER);
        gc.fillArc(px - radius, py - radius, radius * 2, radius * 2, 0, 90, ArcType.ROUND);
        gc.setFill(FACE_INNER);
        gc.fillArc(px - radius + 4, py - radius + 4, radius * 2 - 8, radius * 2 - 8, 0, 90, ArcType.ROUND);

        gc.setStroke(INK);
        gc.setLineWidth(2);
        gc.strokeArc(px - radius, py - radius, radius * 2, radius * 2, 0, 90, ArcType.ROUND);

        for (int deg = 0; deg <= 90; deg += 10) {
            double rad = Math.toRadians(deg);
            boolean major = deg % 30 == 0;
            double tick = major ? 10 : 5;
            gc.setLineWidth(major ? 1.8 : 1);
            gc.setStroke(INK);
            gc.strokeLine(px + (radius - tick) * Math.cos(rad), py - (radius - tick) * Math.sin(rad),
                    px + radius * Math.cos(rad), py - radius * Math.sin(rad));
        }

        double clamped = Math.max(0, Math.min(90, gunElevation));
        double rad = Math.toRadians(clamped);
        double nx = px + radius * 0.82 * Math.cos(rad);
        double ny = py - radius * 0.82 * Math.sin(rad);

        gc.setStroke(ELEVATION_COLOR);
        gc.setLineWidth(2.4);
        gc.strokeLine(px, py, nx, ny);

        double arrow = 10;
        double spread = Math.toRadians(24);
        gc.setLineWidth(1.9);
        gc.strokeLine(nx, ny, nx - arrow * Math.cos(rad - spread), ny + arrow * Math.sin(rad - spread));
        gc.strokeLine(nx, ny, nx - arrow * Math.cos(rad + spread), ny + arrow * Math.sin(rad + spread));

        gc.setFill(INK);
        gc.fillOval(px - 4.5, py - 4.5, 9, 9);

        gc.setFont(Font.font("Courier New", FontWeight.BOLD, 11));
        gc.setFill(INK);
        gc.fillText("0", px + radius - 10, py + 15);
        gc.fillText("90", px - 5, py - radius - 7);

        gc.setFill(Color.web("#9aa3b2"));
        gc.fillText("ELEVATION", 10, h - 12);
    }

    private void drawLabelWithBackground(GraphicsContext gc, String text, double x, double y) {
        double padding = 3;
        double textWidth = text.length() * 8;
        gc.setFill(Color.rgb(216, 218, 221, 0.9));
        gc.fillRect(x - padding, y - 11, textWidth + padding * 2, 15);
        gc.setFill(INK);
        gc.fillText(text, x, y);
    }

    private void drawNeedle(GraphicsContext gc, double cx, double cy, double length, double angleDegrees, Color color, double lineWidth) {
        double rad = Math.toRadians(angleDegrees - 90);
        double x = cx + length * Math.cos(rad);
        double y = cy + length * Math.sin(rad);

        gc.setStroke(color);
        gc.setLineWidth(lineWidth);
        gc.strokeLine(cx, cy, x, y);

        double arrow = 11;
        double spread = Math.toRadians(22);
        gc.setLineWidth(lineWidth * 0.7);
        gc.strokeLine(x, y, x - arrow * Math.cos(rad - spread), y - arrow * Math.sin(rad - spread));
        gc.strokeLine(x, y, x - arrow * Math.cos(rad + spread), y - arrow * Math.sin(rad + spread));
    }

    public void shutdown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.stop();
        if (reportConsumer != null) reportConsumer.stop();
        logger.info("Kafka connections closed safely.");
    }
}
