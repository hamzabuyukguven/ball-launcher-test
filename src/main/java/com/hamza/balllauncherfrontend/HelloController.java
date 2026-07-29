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
import java.util.List;

public class HelloController {

    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);

    private static final double METERS_PER_KNOT_UNIT = 1852.0;
    private static final double GRAVITY = 9.81;

    private static final Color OWNSHIP_COLOR = Color.web("#1f3d5c");
    private static final Color BEARING_COLOR = Color.web("#c0392b");
    private static final Color ELEVATION_COLOR = Color.web("#d98324");
    private static final Color FORBIDDEN_FILL = Color.rgb(107, 34, 34, 0.55);
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
    @FXML private Label muzzleVelocityLabel;
    @FXML private Label statusMessageLabel;

    @FXML private TextField latitudeField;
    @FXML private TextField longitudeField;
    @FXML private ComboBox<String> ballTypeField;
    @FXML private TextArea solutionArea;
    @FXML private TextArea reportsArea;
    @FXML private TextArea forbiddenZoneArea;
    @FXML private TextArea helpArea;
    @FXML private Canvas compassCanvas;
    @FXML private Canvas elevationCanvas;
    @FXML private Button fireButton;
    @FXML private Button slewButton;
    @FXML private Button stowButton;
    @FXML private Button emergencyButton;
    @FXML private ToggleButton unitMeterToggle;
    @FXML private ToggleButton unitKnotToggle;

    private CommandProducer producer;
    private SystemStatusConsumer consumer;
    private SystemReportConsumer reportConsumer;

    private List<double[]> forbiddenSectors;

    private double ownshipHeading = 0;
    private double gunBearing = 0;
    private double gunElevation = 0;
    private double lastX = 0;
    private double lastY = 0;
    private double muzzleVelocity = AppConfig.getDefaultMuzzleVelocity();

    private boolean emergencyActive = false;
    private boolean stowInProgress = false;
    private boolean connected = false;
    private boolean readyToFire = false;
    private boolean aimed = false;
    private boolean bearingWasForbidden = false;

    private boolean solutionValid = false;
    private double solutionLatMeters = 0;
    private double solutionLonMeters = 0;

    private PauseTransition stowTimeout;

    @FXML
    public void initialize() {
        ballTypeField.getItems().addAll("76 MM");
        ballTypeField.getSelectionModel().selectFirst();

        forbiddenSectors = AppConfig.getForbiddenSectors();

        reportsArea.managedProperty().bind(reportsArea.visibleProperty());
        forbiddenZoneArea.managedProperty().bind(forbiddenZoneArea.visibleProperty());
        helpArea.managedProperty().bind(helpArea.visibleProperty());

        buildHelpText();
        seedForbiddenZonePanel();
        reportsArea.setText("--- SYSTEM REPORT LOG ---" + System.lineSeparator());

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

        muzzleVelocityLabel.setText(String.format("Muzzle velocity: %.1f m/s", muzzleVelocity));

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

            double reported = status.getMuzzleVelocity();
            muzzleVelocity = reported > 0 ? reported : AppConfig.getDefaultMuzzleVelocity();
            muzzleVelocityLabel.setText(String.format("Muzzle velocity: %.1f m/s", muzzleVelocity));

            ammoLabel.setText(String.valueOf(status.getAmmoCount()));

            trackForbiddenBearing();

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
                String upper = message.toUpperCase();
                boolean zoneEvent = upper.contains("FORBIDDEN") || upper.contains("NO-FIRE")
                        || upper.contains("NO FIRE") || upper.contains("ZONE");
                Platform.runLater(() -> appendLog(zoneEvent ? forbiddenZoneArea : reportsArea, message));
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

    private void buildHelpText() {
        StringBuilder sb = new StringBuilder();
        sb.append("=== GUN LAUNCHER CONTROL PANEL — OPERATOR GUIDE ===").append(System.lineSeparator());
        sb.append(System.lineSeparator());
        sb.append("COORDINATE FRAME").append(System.lineSeparator());
        sb.append(" Ownship is the origin (0, 0). Latitude and longitude are entered").append(System.lineSeparator());
        sb.append(" in knots relative to ownship and converted to metres before sending.").append(System.lineSeparator());
        sb.append(" 1 kn unit = 1852 m.").append(System.lineSeparator());
        sb.append(System.lineSeparator());
        sb.append("STATUS INDICATORS").append(System.lineSeparator());
        sb.append(" AVAILABILITY Backend service state. Green = ready or idle,").append(System.lineSeparator());
        sb.append(" blue = moving or stowing, red = fault or stop.").append(System.lineSeparator());
        sb.append(" ALIGNMENT ALIGNED once the barrel is on the commanded bearing.").append(System.lineSeparator());
        sb.append(" FIRE SAFETY READY only when the backend clears all interlocks.").append(System.lineSeparator());
        sb.append(System.lineSeparator());
        sb.append("BARREL DISPLAY").append(System.lineSeparator());
        sb.append(" Thick navy needle Ownship heading.").append(System.lineSeparator());
        sb.append(" Thin red needle Barrel bearing on the horizontal axis.").append(System.lineSeparator());
        sb.append(" Amber needle Barrel elevation on the quadrant gauge (0-90).").append(System.lineSeparator());
        sb.append(" Dark red arcs Forbidden sectors. Firing is blocked inside them.").append(System.lineSeparator());
        sb.append(System.lineSeparator());
        sb.append("COMMANDS").append(System.lineSeparator());
        sb.append(" SET MANUAL TARGET Sends the entered coordinates as a manual target.").append(System.lineSeparator());
        sb.append(" BALLISTIC CALCULATION Computes range, bearing, quadrant elevation and").append(System.lineSeparator());
        sb.append(" time of flight. Does not move the barrel.").append(System.lineSeparator());
        sb.append(" SLEW TO TARGET Lays the barrel onto the computed solution.").append(System.lineSeparator());
        sb.append(" Enabled only after a valid solution.").append(System.lineSeparator());
        sb.append(" FIRE Fires along the current barrel bearing. It does").append(System.lineSeparator());
        sb.append(" not read the coordinate fields.").append(System.lineSeparator());
        sb.append(" STOW Returns the barrel to its stowed position.").append(System.lineSeparator());
        sb.append(" EMERGENCY STOP Locks the system. Any other command releases it.").append(System.lineSeparator());
        sb.append(System.lineSeparator());
        sb.append("LOG PANELS").append(System.lineSeparator());
        sb.append(" REPORTS General backend and simulation reports.").append(System.lineSeparator());
        sb.append(" FORBIDDEN ZONE Sector violations and blocked fire attempts.").append(System.lineSeparator());
        sb.append(" Panels are mutually exclusive and keep the newest ").append(AppConfig.getReportsMaxLines());
        sb.append(" lines.").append(System.lineSeparator());
        helpArea.setText(sb.toString());
    }

    private void seedForbiddenZonePanel() {
        StringBuilder sb = new StringBuilder();
        sb.append("--- FORBIDDEN ZONE LOG ---").append(System.lineSeparator());
        if (forbiddenSectors.isEmpty()) {
            sb.append("No forbidden sectors configured.").append(System.lineSeparator());
        } else {
            sb.append("Configured no-fire sectors:").append(System.lineSeparator());
            for (double[] sector : forbiddenSectors) {
                sb.append(String.format(" %6.1f deg -> %6.1f deg%n", sector[0], sector[1]));
            }
        }
        forbiddenZoneArea.setText(sb.toString());
    }

    private void appendLog(TextArea area, String message) {
        area.appendText(String.format("[%s] %s%n", LocalTime.now().withNano(0), message));
        trimArea(area);
        area.setScrollTop(Double.MAX_VALUE);
    }

    private void trimArea(TextArea area) {
        String[] lines = area.getText().split("\n");
        int maxLines = AppConfig.getReportsMaxLines();
        if (lines.length > maxLines) {
            StringBuilder trimmed = new StringBuilder();
            for (int i = lines.length - maxLines; i < lines.length; i++) {
                trimmed.append(lines[i]).append("\n");
            }
            area.setText(trimmed.toString());
        }
    }

    private void togglePanel(TextArea target) {
        boolean makeVisible = !target.isVisible();
        reportsArea.setVisible(false);
        forbiddenZoneArea.setVisible(false);
        helpArea.setVisible(false);
        target.setVisible(makeVisible);
    }

    private void showPanel(TextArea target) {
        reportsArea.setVisible(false);
        forbiddenZoneArea.setVisible(false);
        helpArea.setVisible(false);
        target.setVisible(true);
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

    private double normalizeBearing(double bearing) {
        return ((bearing % 360) + 360) % 360;
    }

    private boolean isBearingForbidden(double bearing) {
        double b = normalizeBearing(bearing);
        for (double[] sector : forbiddenSectors) {
            double start = normalizeBearing(sector[0]);
            double end = normalizeBearing(sector[1]);
            if (start <= end) {
                if (b >= start && b <= end) return true;
            } else if (b >= start || b <= end) {
                return true;
            }
        }
        return false;
    }

    private void trackForbiddenBearing() {
        boolean nowForbidden = isBearingForbidden(gunBearing);
        if (nowForbidden && !bearingWasForbidden) {
            appendLog(forbiddenZoneArea, String.format("Barrel entered forbidden sector at %.2f deg.", gunBearing));
        } else if (!nowForbidden && bearingWasForbidden) {
            appendLog(forbiddenZoneArea, String.format("Barrel cleared forbidden sector at %.2f deg.", gunBearing));
        }
        bearingWasForbidden = nowForbidden;
    }

    private void refreshFireState() {
        fireButton.setDisable(!(connected && readyToFire && !emergencyActive));
        slewButton.setDisable(!(connected && solutionValid && !emergencyActive));
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
            logger.info("SET_MANUAL_TARGET sent X:{} m Y:{} m", telemetry.getTargetX(), telemetry.getTargetY());
            appendLog(reportsArea, String.format("Manual target set to %.1f m / %.1f m.",
                    telemetry.getTargetY(), telemetry.getTargetX()));
            setUiMessage(released ? "Emergency released. Manual target set." : "Manual target set.", false);
        } catch (NumberFormatException e) {
            setUiMessage("Invalid coordinates entered.", true);
        }
    }

    @FXML
    protected void onBallisticCalculationClick() {
        double latMeters;
        double lonMeters;
        try {
            latMeters = Double.parseDouble(latitudeField.getText().trim()) * METERS_PER_KNOT_UNIT;
            lonMeters = Double.parseDouble(longitudeField.getText().trim()) * METERS_PER_KNOT_UNIT;
        } catch (NumberFormatException e) {
            solutionValid = false;
            refreshFireState();
            solutionArea.setText("INPUT ERROR: latitude and longitude must be numeric.");
            setUiMessage("Enter valid target coordinates first.", true);
            return;
        }

        double range = Math.hypot(lonMeters, latMeters);
        double bearing = normalizeBearing(Math.toDegrees(Math.atan2(lonMeters, latMeters)));
        double relativeBearing = normalizeBearing(bearing - ownshipHeading);
        double maxRange = (muzzleVelocity * muzzleVelocity) / GRAVITY;
        boolean forbidden = isBearingForbidden(bearing);

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("TARGET LAT : %10.3f kn%n", latMeters / METERS_PER_KNOT_UNIT));
        sb.append(String.format("TARGET LON : %10.3f kn%n", lonMeters / METERS_PER_KNOT_UNIT));
        sb.append(String.format("SLANT RANGE : %10.1f m%n", range));
        sb.append(String.format("TRUE BEARING : %10.2f deg%n", bearing));
        sb.append(String.format("REL BEARING : %10.2f deg%n", relativeBearing));

        if (forbidden) {
            solutionValid = false;
            sb.append("SOLUTION : REJECTED — TARGET IN FORBIDDEN SECTOR");
            solutionArea.setText(sb.toString());
            appendLog(forbiddenZoneArea, String.format("Solution rejected: target bearing %.2f deg is inside a forbidden sector.", bearing));
            showPanel(forbiddenZoneArea);
            setUiMessage("Target lies inside a forbidden sector.", true);
        } else if (range > maxRange) {
            solutionValid = false;
            sb.append(String.format("SOLUTION : OUT OF RANGE (max %.1f m)", maxRange));
            solutionArea.setText(sb.toString());
            setUiMessage("Target beyond maximum range for current muzzle velocity.", true);
        } else {
            double elevation = 0.5 * Math.toDegrees(Math.asin((range * GRAVITY) / (muzzleVelocity * muzzleVelocity)));
            double tof = (2 * muzzleVelocity * Math.sin(Math.toRadians(elevation))) / GRAVITY;
            solutionValid = true;
            solutionLatMeters = latMeters;
            solutionLonMeters = lonMeters;
            sb.append(String.format("QUADRANT ELEV : %10.2f deg%n", elevation));
            sb.append(String.format("TIME OF FLIGHT: %10.2f s", tof));
            solutionArea.setText(sb.toString());
            appendLog(reportsArea, String.format("Firing solution computed: range %.1f m, QE %.2f deg.", range, elevation));
            setUiMessage("Firing solution computed. Slew available.", false);
        }

        refreshFireState();
    }

    @FXML
    protected void onSlewToTargetClick() {
        if (!solutionValid) {
            setUiMessage("Run ballistic calculation first.", true);
            return;
        }
        boolean released = releaseEmergencyIfNeeded();
        LauncherTelemetry telemetry = new LauncherTelemetry(solutionLonMeters, solutionLatMeters);
        producer.sendTelemetry(solutionLonMeters, solutionLatMeters);
        producer.sendCommand(new LaunchCommand(LauncherAction.USE_TRACKED_TARGET, telemetry));
        logger.info("SLEW to solution lat:{} m lon:{} m", solutionLatMeters, solutionLonMeters);
        appendLog(reportsArea, "Slew command sent to computed solution.");
        setUiMessage(released ? "Emergency released. Slewing to target." : "Slewing to target.", false);
    }

    @FXML
    protected void onFireButtonClick() {
        boolean released = releaseEmergencyIfNeeded();

        if (!readyToFire) {
            setUiMessage("System is not ready to fire.", true);
            return;
        }

        if (isBearingForbidden(gunBearing)) {
            appendLog(forbiddenZoneArea, String.format("FIRE BLOCKED: barrel bearing %.2f deg is inside a forbidden sector.", gunBearing));
            showPanel(forbiddenZoneArea);
            setUiMessage("Fire blocked: barrel is inside a forbidden sector.", true);
            return;
        }

        producer.sendCommand(new LaunchCommand(LauncherAction.FIRE, null));
        logger.info("FIRE sent along current barrel bearing {} deg.", gunBearing);
        appendLog(reportsArea, String.format("Fire request sent along bearing %.2f deg, elevation %.2f deg.", gunBearing, gunElevation));
        setUiMessage(released ? "Emergency released. Fire request sent." : "Fire request sent along current barrel bearing.", false);
    }

    @FXML
    protected void onStowButtonClick() {
        boolean released = releaseEmergencyIfNeeded();
        producer.sendCommand(new LaunchCommand(LauncherAction.STOW, null));
        beginStow();
        appendLog(reportsArea, "Stow command sent.");
        setUiMessage(released ? "Emergency released. Stowing..." : "Stowing...", false);
    }

    @FXML
    protected void onEmergencyStopButtonClick() {
        producer.sendCommand(new LaunchCommand(LauncherAction.EMERGENCY_STOP, null));
        engageEmergency();
        logger.warn("EMERGENCY STOP command sent.");
        appendLog(reportsArea, "EMERGENCY STOP engaged by operator.");
        setUiMessage("EMERGENCY STOP engaged. Send any command to release.", true);
    }

    @FXML
    protected void onReportsButtonClick() {
        togglePanel(reportsArea);
    }

    @FXML
    protected void onForbiddenZoneButtonClick() {
        togglePanel(forbiddenZoneArea);
    }

    @FXML
    protected void onHelpButtonClick() {
        togglePanel(helpArea);
    }

    private LauncherTelemetry readTelemetry() {
        double latMeters = Double.parseDouble(latitudeField.getText().trim()) * METERS_PER_KNOT_UNIT;
        double lonMeters = Double.parseDouble(longitudeField.getText().trim()) * METERS_PER_KNOT_UNIT;
        return new LauncherTelemetry(lonMeters, latMeters);
    }

    private void setUiMessage(String message, boolean isError) {
        statusMessageLabel.setText(message);
        statusMessageLabel.setTextFill(isError ? Color.web("#ff8a8a") : Color.web("#c3c9d4"));
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

        drawForbiddenSectors(gc, cx, cy, radius - 4);

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

    private void drawForbiddenSectors(GraphicsContext gc, double cx, double cy, double radius) {
        if (forbiddenSectors.isEmpty()) {
            return;
        }
        gc.setFill(FORBIDDEN_FILL);
        for (double[] sector : forbiddenSectors) {
            double start = normalizeBearing(sector[0]);
            double end = normalizeBearing(sector[1]);
            if (start <= end) {
                fillSector(gc, cx, cy, radius, start, end);
            } else {
                fillSector(gc, cx, cy, radius, start, 360);
                fillSector(gc, cx, cy, radius, 0, end);
            }
        }
    }

    private void fillSector(GraphicsContext gc, double cx, double cy, double radius, double from, double to) {
        double extent = to - from;
        if (extent <= 0) {
            return;
        }
        gc.fillArc(cx - radius, cy - radius, radius * 2, radius * 2, 90 - to, extent, ArcType.ROUND);
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
