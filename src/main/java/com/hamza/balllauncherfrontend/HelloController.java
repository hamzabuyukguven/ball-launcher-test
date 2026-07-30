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
import javafx.geometry.Pos;
import javafx.scene.Node;
import javafx.scene.canvas.Canvas;
import javafx.scene.canvas.GraphicsContext;
import javafx.scene.control.Button;
import javafx.scene.control.ComboBox;
import javafx.scene.control.Label;
import javafx.scene.control.ListCell;
import javafx.scene.control.ListView;
import javafx.scene.control.TextArea;
import javafx.scene.control.TextField;
import javafx.scene.control.ToggleButton;
import javafx.scene.control.ToggleGroup;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.VBox;
import javafx.scene.paint.Color;
import javafx.scene.shape.ArcType;
import javafx.scene.text.Font;
import javafx.scene.text.FontWeight;
import javafx.util.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

public class HelloController {

    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);

    private static final double METERS_PER_KNOT_UNIT = 1852.0;
    private static final double GRAVITY = 9.81;
    private static final DateTimeFormatter TIME_FORMAT = DateTimeFormatter.ofPattern("HH:mm:ss");

    private static final Color OWNSHIP_COLOR = Color.web("#1f3d5c");
    private static final Color BEARING_COLOR = Color.web("#c0392b");
    private static final Color ELEVATION_COLOR = Color.web("#d98324");
    private static final Color FORBIDDEN_FILL = Color.rgb(140, 28, 28, 0.78);
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

    private static final String HEADER_NORMAL = "-fx-background-color: #18324a; -fx-padding: 11;";
    private static final String HEADER_EMERGENCY = "-fx-background-color: #7e1111; -fx-padding: 11;";

    private static final String STOW_ACTIVE = "-fx-background-color: #4a8cd2; -fx-text-fill: white; -fx-font-weight: bold; -fx-font-size: 15px; -fx-padding: 11; -fx-background-radius: 4;";
    private static final String STOW_BUSY = "-fx-background-color: #9dbde0; -fx-text-fill: #2c4a68; -fx-font-weight: bold; -fx-font-size: 15px; -fx-padding: 11; -fx-background-radius: 4;";

    public enum Severity {
        OK("#2ecc71"),
        INFO("#4a8cd2"),
        WARN("#d98324"),
        ERROR("#e74c3c");

        private final String color;

        Severity(String color) {
            this.color = color;
        }

        public String getColor() {
            return color;
        }
    }

    public static final class LogEntry {
        private final String time;
        private final String code;
        private final String message;
        private final Severity severity;

        LogEntry(String code, Severity severity, String message) {
            this.time = LocalTime.now().format(TIME_FORMAT);
            this.code = code;
            this.severity = severity;
            this.message = message;
        }

        public String getTime() {
            return time;
        }

        public String getCode() {
            return code;
        }

        public String getMessage() {
            return message;
        }

        public Severity getSeverity() {
            return severity;
        }
    }

    @FXML private HBox headerBar;
    @FXML private Label emergencyBanner;
    @FXML private Label connectionLabel;
    @FXML private Label readyLabel;
    @FXML private Label availabilityLabel;
    @FXML private Label aimLabel;
    @FXML private Label ownshipPositionLabel;
    @FXML private Label targetRelativeLabel;
    @FXML private Label targetWorldLabel;
    @FXML private Label targetSolutionLabel;
    @FXML private Label trackedLockLabel;
    @FXML private Label headingLabel;
    @FXML private Label panLabel;
    @FXML private Label tiltLabel;
    @FXML private Label ammoLabel;
    @FXML private Label muzzleVelocityLabel;
    @FXML private Label statusMessageLabel;
    @FXML private Label forbiddenSectorLabel;

    @FXML private TextField latitudeField;
    @FXML private TextField longitudeField;
    @FXML private ComboBox<String> ballTypeField;
    @FXML private TextArea solutionArea;
    @FXML private TextArea helpArea;
    @FXML private VBox reportsPanel;
    @FXML private VBox forbiddenPanel;
    @FXML private ListView<LogEntry> reportsList;
    @FXML private ListView<LogEntry> forbiddenList;
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
    private double ownshipX = 0;
    private double ownshipY = 0;
    private double muzzleVelocity = AppConfig.getDefaultMuzzleVelocity();

    private boolean emergencyActive = false;
    private boolean stowInProgress = false;
    private boolean connected = false;
    private boolean readyToFire = false;
    private boolean aimed = false;
    private boolean lockEngaged = false;
    private boolean bearingWasForbidden = false;

    private boolean solutionValid = false;
    private double solutionRelLat = 0;
    private double solutionRelLon = 0;

    private boolean hasCommandedTarget = false;
    private double commandedRelLat = 0;
    private double commandedRelLon = 0;
    private double commandedWorldX = 0;
    private double commandedWorldY = 0;

    private int backendMessageCounter = 0;

    private PauseTransition stowTimeout;

    @FXML
    public void initialize() {
        ballTypeField.getItems().addAll("A", "B", "C");
        ballTypeField.getSelectionModel().selectFirst();

        forbiddenSectors = AppConfig.getForbiddenSectors();

        reportsPanel.managedProperty().bind(reportsPanel.visibleProperty());
        forbiddenPanel.managedProperty().bind(forbiddenPanel.visibleProperty());
        helpArea.managedProperty().bind(helpArea.visibleProperty());

        reportsList.setCellFactory(list -> createLogCell());
        forbiddenList.setCellFactory(list -> createLogCell());
        reportsList.setFocusTraversable(false);
        forbiddenList.setFocusTraversable(false);

        buildHelpText();
        updateForbiddenSectorLabel();

        logReport("SYS-INIT", Severity.INFO, "Control panel started. Awaiting backend status.");
        if (forbiddenSectors.isEmpty()) {
            logForbidden("FZ-CFG", Severity.WARN, "No forbidden sectors configured.");
        } else {
            for (double[] sector : forbiddenSectors) {
                logForbidden("FZ-CFG", Severity.INFO, String.format(
                        "No-fire sector loaded: %.1f deg to %.1f deg relative to bow.", sector[0], sector[1]));
            }
        }

        ToggleGroup unitGroup = new ToggleGroup();
        unitMeterToggle.setToggleGroup(unitGroup);
        unitKnotToggle.setToggleGroup(unitGroup);
        unitGroup.selectedToggleProperty().addListener((obs, old, sel) -> {
            if (sel == null) {
                old.setSelected(true);
            } else {
                updateOwnshipAndTargetPanel();
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

            if (lockEngaged) {
                trackedLockLabel.setText(aimed ? "LOCK: ON TARGET" : "LOCK: SLEWING");
                trackedLockLabel.setTextFill(aimed ? Color.web("#5dcaa5") : Color.web("#efb857"));
            }

            ownshipX = status.getXCoordinate();
            ownshipY = status.getYCoordinate();
            updateOwnshipAndTargetPanel();

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

            updateForbiddenSectorLabel();
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
                Platform.runLater(() -> routeBackendMessage(message));
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

    private ListCell<LogEntry> createLogCell() {
        return new ListCell<>() {
            @Override
            protected void updateItem(LogEntry entry, boolean empty) {
                super.updateItem(entry, empty);
                if (empty || entry == null) {
                    setText(null);
                    setGraphic(null);
                    setStyle("-fx-background-color: transparent;");
                    return;
                }

                Region chip = new Region();
                chip.setMinSize(12, 12);
                chip.setPrefSize(12, 12);
                chip.setMaxSize(12, 12);
                chip.setStyle("-fx-background-color: " + entry.getSeverity().getColor() + "; -fx-background-radius: 2;");

                Label time = new Label(entry.getTime());
                time.setMinWidth(60);
                time.setStyle("-fx-text-fill: #7f899a; -fx-font-family: 'Courier New'; -fx-font-size: 11px;");

                Label code = new Label(entry.getCode());
                code.setMinWidth(80);
                code.setStyle("-fx-text-fill: " + entry.getSeverity().getColor()
                        + "; -fx-font-family: 'Courier New'; -fx-font-size: 11px; -fx-font-weight: bold;");

                Label message = new Label(entry.getMessage());
                message.setWrapText(true);
                message.setStyle("-fx-text-fill: #d5dbe4; -fx-font-family: 'Courier New'; -fx-font-size: 11px;");
                HBox.setHgrow(message, Priority.ALWAYS);

                HBox row = new HBox(10, chip, time, code, message);
                row.setAlignment(Pos.CENTER_LEFT);
                row.setStyle("-fx-padding: 5 8 5 8;");

                setGraphic(row);
                setStyle("-fx-background-color: transparent;");
            }
        };
    }

    private void logReport(String code, Severity severity, String message) {
        pushEntry(reportsList, new LogEntry(code, severity, message));
    }

    private void logForbidden(String code, Severity severity, String message) {
        pushEntry(forbiddenList, new LogEntry(code, severity, message));
    }

    private void pushEntry(ListView<LogEntry> list, LogEntry entry) {
        list.getItems().add(entry);
        int max = AppConfig.getReportsMaxLines();
        while (list.getItems().size() > max) {
            list.getItems().remove(0);
        }
        list.scrollTo(list.getItems().size() - 1);
    }

    private void routeBackendMessage(String message) {
        String upper = message.toUpperCase();
        boolean zoneEvent = upper.contains("FORBIDDEN") || upper.contains("NO-FIRE")
                || upper.contains("NO FIRE") || upper.contains("ZONE");

        Severity severity;
        if (upper.contains("FAULT") || upper.contains("ERROR") || upper.contains("FAIL")
                || upper.contains("BLOCK") || upper.contains("REJECT") || upper.contains("EMERGENCY")) {
            severity = Severity.ERROR;
        } else if (upper.contains("WARN") || upper.contains("CAUTION") || upper.contains("NOT READY")) {
            severity = Severity.WARN;
        } else if (upper.contains("OK") || upper.contains("SUCCESS") || upper.contains("COMPLETE")
                || upper.contains("READY") || upper.contains("ALIGNED")) {
            severity = Severity.OK;
        } else {
            severity = Severity.INFO;
        }

        backendMessageCounter++;
        String code = String.format("BKD-%03d", backendMessageCounter);

        if (zoneEvent) {
            logForbidden(code, severity, message);
        } else {
            logReport(code, severity, message);
        }
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
        sb.append("  Latitude and longitude are entered in metres RELATIVE to ownship,").append(System.lineSeparator());
        sb.append("  so ownship is always (0, 0) from the operator's point of view.").append(System.lineSeparator());
        sb.append("  Before transmission the panel adds the ownship world position and").append(System.lineSeparator());
        sb.append("  sends absolute world coordinates, which is what the backend expects.").append(System.lineSeparator());
        sb.append("  The readout can be switched between metres and knot units").append(System.lineSeparator());
        sb.append("  (1 kn unit = 1852 m).").append(System.lineSeparator());
        sb.append(System.lineSeparator());
        sb.append("STATUS INDICATORS").append(System.lineSeparator());
        sb.append("  AVAILABILITY  Backend service state. Green = ready or idle,").append(System.lineSeparator());
        sb.append("                blue = moving or stowing, red = fault or stop.").append(System.lineSeparator());
        sb.append("  ALIGNMENT     ALIGNED once the barrel is on the commanded bearing.").append(System.lineSeparator());
        sb.append("  FIRE SAFETY   READY only when the backend clears all interlocks.").append(System.lineSeparator());
        sb.append("  LOCK          NOT ENGAGED until a slew is commanded, then SLEWING,").append(System.lineSeparator());
        sb.append("                then ON TARGET once the backend confirms alignment.").append(System.lineSeparator());
        sb.append(System.lineSeparator());
        sb.append("BARREL DISPLAY").append(System.lineSeparator());
        sb.append("  Thick navy needle  Ownship heading.").append(System.lineSeparator());
        sb.append("  Thin red needle    Barrel bearing on the horizontal axis.").append(System.lineSeparator());
        sb.append("  Amber needle       Barrel elevation on the quadrant gauge (0-90).").append(System.lineSeparator());
        sb.append("  Dark red arc       No-fire sector astern of ownship, 30 degrees to").append(System.lineSeparator());
        sb.append("                     each side. It is defined against the bow, so it").append(System.lineSeparator());
        sb.append("                     rotates as the ship turns.").append(System.lineSeparator());
        sb.append(System.lineSeparator());
        sb.append("COMMANDS").append(System.lineSeparator());
        sb.append("  SET MANUAL TARGET      Sends the entered position as a manual target.").append(System.lineSeparator());
        sb.append("  BALLISTIC CALCULATION  Computes range, bearing, quadrant elevation and").append(System.lineSeparator());
        sb.append("                         time of flight. Does not move the barrel.").append(System.lineSeparator());
        sb.append("  SLEW TO TARGET         Lays the barrel onto the computed solution and").append(System.lineSeparator());
        sb.append("                         engages the lock. Needs a valid solution first.").append(System.lineSeparator());
        sb.append("  FIRE                   Fires along the current barrel bearing. It does").append(System.lineSeparator());
        sb.append("                         not read the coordinate fields.").append(System.lineSeparator());
        sb.append("  STOW                   Returns the barrel to its stowed position.").append(System.lineSeparator());
        sb.append("  EMERGENCY STOP         Locks the system. Any other command releases it.").append(System.lineSeparator());
        sb.append(System.lineSeparator());
        sb.append("LOG PANELS").append(System.lineSeparator());
        sb.append("  Each entry carries a severity chip, a message code and the text.").append(System.lineSeparator());
        sb.append("  Green = normal completion, blue = information, amber = caution,").append(System.lineSeparator());
        sb.append("  red = fault or blocked action.").append(System.lineSeparator());
        sb.append("  Codes: SYS = panel lifecycle, CMD = command dispatch,").append(System.lineSeparator());
        sb.append("         TGT = targeting, SOL = firing solution, EMG = emergency,").append(System.lineSeparator());
        sb.append("         FZ  = forbidden zone, BKD = backend originated report.").append(System.lineSeparator());
        sb.append("  Panels are mutually exclusive and keep the newest ").append(AppConfig.getReportsMaxLines());
        sb.append(" entries.").append(System.lineSeparator());
        helpArea.setText(sb.toString());
    }

    private void togglePanel(Node target) {
        boolean makeVisible = !target.isVisible();
        reportsPanel.setVisible(false);
        forbiddenPanel.setVisible(false);
        helpArea.setVisible(false);
        target.setVisible(makeVisible);
    }

    private void showPanel(Node target) {
        reportsPanel.setVisible(false);
        forbiddenPanel.setVisible(false);
        helpArea.setVisible(false);
        target.setVisible(true);
    }

    private void updateOwnshipAndTargetPanel() {
        boolean meters = unitMeterToggle.isSelected();
        String unit = meters ? "m" : "kn";
        double divisor = meters ? 1.0 : METERS_PER_KNOT_UNIT;

        ownshipPositionLabel.setText(String.format("Ownship  X: %.2f %s   Y: %.2f %s",
                ownshipX / divisor, unit, ownshipY / divisor, unit));

        if (!hasCommandedTarget) {
            targetRelativeLabel.setText("Target rel   X: --   Y: --");
            targetWorldLabel.setText("Target world X: --   Y: --");
            targetSolutionLabel.setText("Range: --   Bearing: --");
            return;
        }

        targetRelativeLabel.setText(String.format("Target rel   X: %.2f %s   Y: %.2f %s",
                commandedRelLon / divisor, unit, commandedRelLat / divisor, unit));
        targetWorldLabel.setText(String.format("Target world X: %.2f %s   Y: %.2f %s",
                commandedWorldX / divisor, unit, commandedWorldY / divisor, unit));

        double range = Math.hypot(commandedRelLon, commandedRelLat);
        double bearing = normalizeBearing(Math.toDegrees(Math.atan2(commandedRelLon, commandedRelLat)));
        targetSolutionLabel.setText(String.format("Range: %.1f m   Bearing: %.2f deg", range, bearing));
    }

    private void updateForbiddenSectorLabel() {
        if (forbiddenSectors.isEmpty()) {
            forbiddenSectorLabel.setText("NO FORBIDDEN SECTORS CONFIGURED");
            return;
        }
        StringBuilder sb = new StringBuilder("ACTIVE NO-FIRE ARC   ");
        boolean first = true;
        for (double[] sector : absoluteForbiddenSectors()) {
            if (!first) {
                sb.append("   |   ");
            }
            sb.append(String.format("%.1f° - %.1f°", sector[0], sector[1]));
            first = false;
        }
        sb.append(String.format("      OWNSHIP HEADING %.1f°", ownshipHeading));
        forbiddenSectorLabel.setText(sb.toString());
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

    private List<double[]> absoluteForbiddenSectors() {
        List<double[]> absolute = new ArrayList<>();
        for (double[] sector : forbiddenSectors) {
            absolute.add(new double[]{
                    normalizeBearing(sector[0] + ownshipHeading),
                    normalizeBearing(sector[1] + ownshipHeading)
            });
        }
        return absolute;
    }

    private boolean isBearingForbidden(double bearing) {
        double b = normalizeBearing(bearing);
        for (double[] sector : absoluteForbiddenSectors()) {
            double start = sector[0];
            double end = sector[1];
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
            logForbidden("FZ-ENTR", Severity.ERROR,
                    String.format("Barrel entered no-fire arc at %.2f deg.", gunBearing));
        } else if (!nowForbidden && bearingWasForbidden) {
            logForbidden("FZ-EXIT", Severity.OK,
                    String.format("Barrel cleared no-fire arc at %.2f deg.", gunBearing));
        }
        bearingWasForbidden = nowForbidden;
    }

    private void refreshFireState() {
        fireButton.setDisable(emergencyActive);
        slewButton.setDisable(!solutionValid || emergencyActive);
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
        clearLock();
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
        logReport("EMG-CLR", Severity.OK, "Emergency stop released by the next command.");
        logger.info("Emergency stop auto-cleared by new command.");
        return true;
    }

    private void clearLock() {
        lockEngaged = false;
        trackedLockLabel.setText("LOCK: NOT ENGAGED");
        trackedLockLabel.setTextFill(Color.web("#9aa3b2"));
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

    private void rememberTarget(double relLat, double relLon, double worldX, double worldY) {
        commandedRelLat = relLat;
        commandedRelLon = relLon;
        commandedWorldX = worldX;
        commandedWorldY = worldY;
        hasCommandedTarget = true;
        updateOwnshipAndTargetPanel();
    }

    @FXML
    protected void onSetTargetButtonClick() {
        double relLat;
        double relLon;
        try {
            relLat = Double.parseDouble(latitudeField.getText().trim());
            relLon = Double.parseDouble(longitudeField.getText().trim());
        } catch (NumberFormatException e) {
            logReport("TGT-ERR", Severity.ERROR, "Manual target rejected: coordinates are not numeric.");
            setUiMessage("Invalid coordinates entered.", true);
            return;
        }

        boolean released = releaseEmergencyIfNeeded();

        double worldX = ownshipX + relLon;
        double worldY = ownshipY + relLat;

        LauncherTelemetry telemetry = new LauncherTelemetry(worldX, worldY);
        producer.sendTelemetry(worldX, worldY);
        producer.sendCommand(new LaunchCommand(LauncherAction.SET_MANUAL_TARGET, telemetry));

        rememberTarget(relLat, relLon, worldX, worldY);
        logger.info("SET_MANUAL_TARGET rel({}, {}) -> world({}, {})", relLon, relLat, worldX, worldY);
        logReport("TGT-SET", Severity.OK, String.format(
                "Manual target accepted. Relative %.1f / %.1f m, world %.1f / %.1f m.",
                relLon, relLat, worldX, worldY));
        setUiMessage(released ? "Emergency released. Manual target set." : "Manual target set.", false);
    }

    @FXML
    protected void onBallisticCalculationClick() {
        double relLat;
        double relLon;
        try {
            relLat = Double.parseDouble(latitudeField.getText().trim());
            relLon = Double.parseDouble(longitudeField.getText().trim());
        } catch (NumberFormatException e) {
            solutionValid = false;
            refreshFireState();
            solutionArea.setText("INPUT ERROR: latitude and longitude must be numeric.");
            logReport("SOL-ERR", Severity.ERROR, "Ballistic calculation aborted: coordinates are not numeric.");
            setUiMessage("Enter valid target coordinates first.", true);
            return;
        }

        double range = Math.hypot(relLon, relLat);
        double bearing = normalizeBearing(Math.toDegrees(Math.atan2(relLon, relLat)));
        double relativeBearing = normalizeBearing(bearing - ownshipHeading);
        double maxRange = (muzzleVelocity * muzzleVelocity) / GRAVITY;
        boolean forbidden = isBearingForbidden(bearing);

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("TARGET REL LAT: %10.1f m%n", relLat));
        sb.append(String.format("TARGET REL LON: %10.1f m%n", relLon));
        sb.append(String.format("SLANT RANGE   : %10.1f m%n", range));
        sb.append(String.format("TRUE BEARING  : %10.2f deg%n", bearing));
        sb.append(String.format("REL BEARING   : %10.2f deg%n", relativeBearing));

        if (forbidden) {
            solutionValid = false;
            sb.append("SOLUTION      : REJECTED — TARGET IN NO-FIRE ARC");
            solutionArea.setText(sb.toString());
            logForbidden("FZ-SOL", Severity.ERROR, String.format(
                    "Solution rejected: target bearing %.2f deg lies in the no-fire arc.", bearing));
            showPanel(forbiddenPanel);
            setUiMessage("Target lies inside the no-fire arc.", true);
        } else if (range > maxRange) {
            solutionValid = false;
            sb.append(String.format("SOLUTION      : OUT OF RANGE (max %.1f m)", maxRange));
            solutionArea.setText(sb.toString());
            logReport("SOL-RNG", Severity.WARN, String.format(
                    "Solution rejected: range %.1f m exceeds maximum %.1f m.", range, maxRange));
            setUiMessage("Target beyond maximum range for current muzzle velocity.", true);
        } else {
            double elevation = 0.5 * Math.toDegrees(Math.asin((range * GRAVITY) / (muzzleVelocity * muzzleVelocity)));
            double tof = (2 * muzzleVelocity * Math.sin(Math.toRadians(elevation))) / GRAVITY;
            solutionValid = true;
            solutionRelLat = relLat;
            solutionRelLon = relLon;
            sb.append(String.format("QUADRANT ELEV : %10.2f deg%n", elevation));
            sb.append(String.format("TIME OF FLIGHT: %10.2f s", tof));
            solutionArea.setText(sb.toString());
            logReport("SOL-OK", Severity.OK, String.format(
                    "Firing solution computed. Range %.1f m, QE %.2f deg, TOF %.2f s.", range, elevation, tof));
            setUiMessage("Firing solution computed. Slew available.", false);
        }

        refreshFireState();
    }

    @FXML
    protected void onSlewToTargetClick() {
        if (!solutionValid) {
            logReport("CMD-SLEW", Severity.WARN, "Slew rejected: no valid firing solution.");
            setUiMessage("Run ballistic calculation first.", true);
            return;
        }

        boolean released = releaseEmergencyIfNeeded();

        double worldX = ownshipX + solutionRelLon;
        double worldY = ownshipY + solutionRelLat;

        LauncherTelemetry telemetry = new LauncherTelemetry(worldX, worldY);
        producer.sendTelemetry(worldX, worldY);
        producer.sendCommand(new LaunchCommand(LauncherAction.USE_TRACKED_TARGET, telemetry));

        rememberTarget(solutionRelLat, solutionRelLon, worldX, worldY);

        lockEngaged = true;
        trackedLockLabel.setText("LOCK: SLEWING");
        trackedLockLabel.setTextFill(Color.web("#efb857"));

        logger.info("SLEW rel({}, {}) -> world({}, {})", solutionRelLon, solutionRelLat, worldX, worldY);
        logReport("CMD-SLEW", Severity.INFO, String.format(
                "Slew engaged. World target %.1f / %.1f m.", worldX, worldY));
        setUiMessage(released ? "Emergency released. Slewing to target." : "Slewing to target.", false);
    }

    @FXML
    protected void onFireButtonClick() {
        boolean released = releaseEmergencyIfNeeded();

        if (isBearingForbidden(gunBearing)) {
            logForbidden("FZ-FIRE", Severity.ERROR, String.format(
                    "Fire blocked: barrel bearing %.2f deg is inside the no-fire arc.", gunBearing));
            showPanel(forbiddenPanel);
            setUiMessage("Fire blocked: barrel is inside the no-fire arc.", true);
            return;
        }

        if (!readyToFire) {
            logReport("CMD-FIRE", Severity.WARN, "Fire request sent while the backend reports NOT READY.");
        }

        producer.sendCommand(new LaunchCommand(LauncherAction.FIRE, null));
        logger.info("FIRE sent along current barrel bearing {} deg.", gunBearing);
        logReport("CMD-FIRE", Severity.OK, String.format(
                "Fire request sent along bearing %.2f deg, elevation %.2f deg.", gunBearing, gunElevation));
        setUiMessage(released ? "Emergency released. Fire request sent." : "Fire request sent along current barrel bearing.", false);
    }

    @FXML
    protected void onStowButtonClick() {
        boolean released = releaseEmergencyIfNeeded();
        producer.sendCommand(new LaunchCommand(LauncherAction.STOW, null));
        beginStow();
        clearLock();
        logReport("CMD-STOW", Severity.INFO, "Stow command sent. Waiting for the backend to confirm.");
        setUiMessage(released ? "Emergency released. Stowing..." : "Stowing...", false);
    }

    @FXML
    protected void onEmergencyStopButtonClick() {
        producer.sendCommand(new LaunchCommand(LauncherAction.EMERGENCY_STOP, null));
        engageEmergency();
        logger.warn("EMERGENCY STOP command sent.");
        logReport("EMG-STOP", Severity.ERROR, "Emergency stop engaged by the operator.");
        setUiMessage("EMERGENCY STOP engaged. Send any command to release.", true);
    }

    @FXML
    protected void onReportsButtonClick() {
        togglePanel(reportsPanel);
    }

    @FXML
    protected void onForbiddenZoneButtonClick() {
        togglePanel(forbiddenPanel);
    }

    @FXML
    protected void onHelpButtonClick() {
        togglePanel(helpArea);
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
        double radius = Math.min(w, h) / 2 - 20;

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
            double tick = major ? 10 : 5;
            gc.setLineWidth(major ? 1.8 : 1);
            gc.setStroke(INK);
            gc.strokeLine(cx + (radius - tick) * Math.cos(rad), cy + (radius - tick) * Math.sin(rad),
                    cx + radius * Math.cos(rad), cy + radius * Math.sin(rad));
        }

        drawNeedle(gc, cx, cy, radius * 0.58, ownshipHeading, OWNSHIP_COLOR, 6);
        drawNeedle(gc, cx, cy, radius * 0.80, gunBearing, BEARING_COLOR, 2.2);

        gc.setFont(Font.font("Courier New", FontWeight.BOLD, 11));
        drawLabelWithBackground(gc, "0", cx - 4, cy - radius + 18);
        drawLabelWithBackground(gc, "90", cx + radius - 24, cy + 4);
        drawLabelWithBackground(gc, "180", cx - 11, cy + radius - 8);
        drawLabelWithBackground(gc, "270", cx - radius + 5, cy + 4);

        gc.setFill(INK);
        gc.fillOval(cx - 5, cy - 5, 10, 10);
        gc.setFill(Color.web("#e07856"));
        gc.fillOval(cx - 2.5, cy - 2.5, 5, 5);
    }

    private void drawForbiddenSectors(GraphicsContext gc, double cx, double cy, double radius) {
        List<double[]> sectors = absoluteForbiddenSectors();
        if (sectors.isEmpty()) {
            return;
        }
        gc.setFill(FORBIDDEN_FILL);
        for (double[] sector : sectors) {
            double start = sector[0];
            double end = sector[1];
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
        double px = 30;
        double py = h - 30;
        double radius = Math.min(w - 52, py - 34);

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
        gc.fillText("0", px + radius + 4, py + 4);
        gc.fillText("90", px - 6, py - radius - 8);
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
