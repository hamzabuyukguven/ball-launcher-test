package com.hamza.balllauncherfrontend;

import com.hamza.balllauncherfrontend.kafka.CommandProducer;
import com.hamza.balllauncherfrontend.kafka.LauncherAction;
import com.hamza.balllauncherfrontend.kafka.LauncherTelemetry;
import com.hamza.balllauncherfrontend.kafka.SystemReportConsumer;
import com.hamza.balllauncherfrontend.kafka.SystemStatus;
import com.hamza.balllauncherfrontend.kafka.SystemStatusConsumer;
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

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class HelloController {
    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);
    private static final DateTimeFormatter TIME_FORMAT = DateTimeFormatter
            .ofPattern("HH:mm:ss")
            .withZone(ZoneId.systemDefault());

    @FXML private Label connectionStatusLabel;
    @FXML private Label availabilityLabel;
    @FXML private Label coordinatesLabel;
    @FXML private Label panLabel;
    @FXML private Label tiltLabel;
    @FXML private Label ammoLabel;
    @FXML private Label aimLabel;
    @FXML private Label readyLabel;
    @FXML private Label statusMessageLabel;
    @FXML private TextField targetXField;
    @FXML private TextField targetYField;
    @FXML private TextField targetZField;
    @FXML private TextArea reportArea;
    @FXML private Canvas compassCanvas;
    @FXML private Button fireButton;

    private CommandProducer commandProducer;
    private SystemStatusConsumer statusConsumer;
    private SystemReportConsumer reportConsumer;
    private Thread statusThread;
    private Thread reportThread;
    private volatile SystemStatus latestStatus = new SystemStatus();
    private volatile long lastStatusReceivedMillis;
    private volatile boolean statusFresh;
    private volatile boolean trackedTargetSelected = true;
    private final ScheduledExecutorService statusWatchdog = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread thread = new Thread(r, "frontend-status-watchdog");
        thread.setDaemon(true);
        return thread;
    });

    @FXML
    public void initialize() {
        drawCompass(0.0);
        startKafkaClients();
        statusWatchdog.scheduleAtFixedRate(this::checkStatusFreshness, 4, 1, TimeUnit.SECONDS);
    }

    private void startKafkaClients() {
        try {
            commandProducer = new CommandProducer();
            statusConsumer = new SystemStatusConsumer(this::applyStatus);
            reportConsumer = new SystemReportConsumer(this::applyReport);

            statusThread = new Thread(statusConsumer, "frontend-status-consumer");
            reportThread = new Thread(reportConsumer, "frontend-report-consumer");
            statusThread.setDaemon(true);
            reportThread.setDaemon(true);
            statusThread.start();
            reportThread.start();

            setMessage("Kafka istemcileri başlatıldı: " + AppConfig.kafkaBootstrapServers(), false);
        } catch (Exception e) {
            logger.error("Kafka clients could not be started", e);
            setMessage("Kafka başlatılamadı: " + safeMessage(e), true);
        }
    }

    @FXML
    private void onSetTarget() {
        LauncherTelemetry telemetry = readTarget();
        if (telemetry == null) return;
        trackedTargetSelected = false;
        sendCommand(LauncherAction.SET_MANUAL_TARGET, telemetry,
                String.format("Hedef gönderildi: X=%.2f Y=%.2f Z=%.2f",
                        telemetry.getTargetX(), telemetry.getTargetY(), telemetry.getTargetZ()));
    }

    @FXML
    private void onUseTrackedTarget() {
        trackedTargetSelected = true;
        sendCommand(LauncherAction.USE_TRACKED_TARGET, null,
                "Simulation target stream'i aktif hedef kaynağı olarak seçildi.");
    }

    @FXML
    private void onFire() {
        if (!statusFresh || !latestStatus.isConnected()) {
            setMessage("Atış isteği gönderilmedi: simulation bağlantısı hazır değil.", true);
            return;
        }

        LauncherTelemetry optionalTarget = null;
        if (!trackedTargetSelected
                && (!targetXField.getText().isBlank() || !targetYField.getText().isBlank())) {
            optionalTarget = readTarget();
            if (optionalTarget == null) return;
        }

        sendCommand(LauncherAction.FIRE, optionalTarget,
                "Atış isteği kuyruğa alındı; backend hizalama ve emniyet koşullarını bekleyecek.");
    }

    @FXML
    private void onStow() {
        sendCommand(LauncherAction.STOW, null, "Top stow konumuna gönderildi.");
    }

    @FXML
    private void onEmergencyStop() {
        sendCommand(LauncherAction.EMERGENCY_STOP, null, "ACİL DURDURMA komutu gönderildi.");
    }

    @FXML
    private void onClearEmergencyStop() {
        sendCommand(LauncherAction.CLEAR_EMERGENCY_STOP, null,
                "Acil durdurma kilidini kaldırma komutu gönderildi.");
    }

    private LauncherTelemetry readTarget() {
        try {
            double x = parseFinite(targetXField, "Hedef X");
            double y = parseFinite(targetYField, "Hedef Y");
            double z = targetZField.getText().isBlank() ? 0.0 : parseFinite(targetZField, "Hedef Z");
            return new LauncherTelemetry(x, y, z);
        } catch (IllegalArgumentException e) {
            setMessage(e.getMessage(), true);
            return null;
        }
    }

    private double parseFinite(TextField field, String label) {
        String text = field.getText() == null ? "" : field.getText().trim().replace(',', '.');
        if (text.isBlank()) {
            throw new IllegalArgumentException(label + " boş bırakılamaz.");
        }
        try {
            double value = Double.parseDouble(text);
            if (!Double.isFinite(value)) {
                throw new NumberFormatException("not finite");
            }
            return value;
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(label + " geçerli bir sayı olmalıdır.");
        }
    }

    private void sendCommand(
            LauncherAction action,
            LauncherTelemetry telemetry,
            String successMessage) {
        if (commandProducer == null) {
            setMessage("Kafka producer hazır değil.", true);
            return;
        }

        commandProducer.send(action, telemetry).whenComplete((ignored, error) ->
                javafx.application.Platform.runLater(() -> {
                    if (error != null) {
                        setMessage(action + " gönderilemedi: " + safeMessage(error), true);
                    } else {
                        setMessage(successMessage, false);
                    }
                }));
    }

    private void applyStatus(SystemStatus status) {
        if (status == null) return;
        latestStatus = status;
        lastStatusReceivedMillis = System.currentTimeMillis();
        statusFresh = true;

        connectionStatusLabel.setText(status.isConnected() ? "BAĞLI" : "BAĞLANTI YOK");
        connectionStatusLabel.setTextFill(status.isConnected() ? Color.FORESTGREEN : Color.FIREBRICK);
        availabilityLabel.setText(valueOr(status.getAvailability(), "BİLİNMİYOR"));
        coordinatesLabel.setText(String.format("X: %.2f m   Y: %.2f m",
                status.getXCoordinate(), status.getYCoordinate()));
        panLabel.setText(String.format("Pan: %.2f°", status.getPlatformAngle()));
        tiltLabel.setText(String.format("Tilt: %.2f°", status.getCannonAngle()));
        ammoLabel.setText(String.format("%d × %s", status.getAmmoCount(), valueOr(status.getAmmoType(), "N/A")));
        aimLabel.setText(status.isAimed() ? "HİZALI" : "HİZALANIYOR");
        aimLabel.setTextFill(status.isAimed() ? Color.FORESTGREEN : Color.DARKORANGE);
        readyLabel.setText(status.isReadyToFire() ? "ATEŞE HAZIR" : "EMNİYET KİLİTLİ");
        readyLabel.setTextFill(status.isReadyToFire() ? Color.FORESTGREEN : Color.FIREBRICK);
        fireButton.setDisable(!status.isConnected());
        drawCompass(status.getPlatformAngle());

    }

    private void checkStatusFreshness() {
        long last = lastStatusReceivedMillis;
        if (!statusFresh || last <= 0 || System.currentTimeMillis() - last <= 4_000) {
            return;
        }
        statusFresh = false;
        javafx.application.Platform.runLater(() -> {
            connectionStatusLabel.setText("BAĞLANTI YOK");
            connectionStatusLabel.setTextFill(Color.FIREBRICK);
            availabilityLabel.setText("BACKEND/KAFKA BEKLENİYOR");
            readyLabel.setText("EMNİYET KİLİTLİ");
            readyLabel.setTextFill(Color.FIREBRICK);
            fireButton.setDisable(true);
            setMessage("Dört saniyedir backend durum mesajı alınmadı.", true);
        });
    }

    private void applyReport(SystemStatus report) {
        if (report == null) return;
        appendReport(report.getTimestamp(), valueOr(report.getReportMessage(), "Rapor mesajı yok"));
    }

    private void appendReport(long timestamp, String message) {
        long safeTimestamp = timestamp > 0 ? timestamp : System.currentTimeMillis();
        reportArea.appendText("[" + TIME_FORMAT.format(Instant.ofEpochMilli(safeTimestamp)) + "] "
                + message + System.lineSeparator());
    }

    private void drawCompass(double angleDegrees) {
        GraphicsContext gc = compassCanvas.getGraphicsContext2D();
        double width = compassCanvas.getWidth();
        double height = compassCanvas.getHeight();
        double cx = width / 2.0;
        double cy = height / 2.0;
        double radius = Math.min(width, height) * 0.38;

        gc.clearRect(0, 0, width, height);
        gc.setStroke(Color.SLATEGRAY);
        gc.setLineWidth(2.0);
        gc.strokeOval(cx - radius, cy - radius, radius * 2.0, radius * 2.0);

        gc.setFill(Color.DARKSLATEGRAY);
        gc.fillText("N", cx - 4, cy - radius - 8);
        gc.fillText("E", cx + radius + 8, cy + 4);
        gc.fillText("S", cx - 4, cy + radius + 18);
        gc.fillText("W", cx - radius - 18, cy + 4);

        double radians = Math.toRadians(angleDegrees - 90.0);
        double endX = cx + Math.cos(radians) * radius * 0.85;
        double endY = cy + Math.sin(radians) * radius * 0.85;
        gc.setStroke(Color.DODGERBLUE);
        gc.setLineWidth(4.0);
        gc.strokeLine(cx, cy, endX, endY);
        gc.setFill(Color.DODGERBLUE);
        gc.fillOval(cx - 5, cy - 5, 10, 10);
    }

    private void setMessage(String message, boolean error) {
        statusMessageLabel.setText(message);
        statusMessageLabel.setTextFill(error ? Color.FIREBRICK : Color.DARKSLATEGRAY);
    }

    private String safeMessage(Throwable error) {
        Throwable current = error;
        while (current.getCause() != null) current = current.getCause();
        return current.getMessage() == null ? current.getClass().getSimpleName() : current.getMessage();
    }

    private String valueOr(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    public void shutdown() {
        statusWatchdog.shutdownNow();
        if (statusConsumer != null) statusConsumer.close();
        if (reportConsumer != null) reportConsumer.close();
        if (commandProducer != null) commandProducer.close();
        joinQuietly(statusThread);
        joinQuietly(reportThread);
    }

    private void joinQuietly(Thread thread) {
        if (thread == null) return;
        try {
            thread.join(1_000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
