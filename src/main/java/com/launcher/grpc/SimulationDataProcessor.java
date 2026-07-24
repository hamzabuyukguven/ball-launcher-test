package com.launcher.grpc;

import com.heybeliada.grpc.GunInfo;
import com.heybeliada.grpc.GunStatusInfo;
import com.heybeliada.grpc.Heartbeat;
import com.heybeliada.grpc.PlatformPositionInfo;
import com.heybeliada.grpc.TargetPositionInfo;
import com.launcher.control.KalmanFilter;
import com.launcher.simulationtest.LauncherControlService;
import com.launcher.kafka.SystemStatusPublisher;
import com.launcher.kafka.model.SystemStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class SimulationDataProcessor {
    private static final Logger logger = LoggerFactory.getLogger(SimulationDataProcessor.class);

    private final KalmanFilter ownshipKalmanFilter;
    private final KalmanFilter targetKalmanFilter;

    private final SystemStatusPublisher kafkaPublisher;
    private final SystemStatus currentStatus;

    private LauncherControlService controlService;

    public SimulationDataProcessor(SystemStatusPublisher kafkaPublisher) {
        this.kafkaPublisher = kafkaPublisher;
        this.ownshipKalmanFilter = new KalmanFilter(0.1);
        this.targetKalmanFilter = new KalmanFilter(0.1);
        this.currentStatus = new SystemStatus();
    }

    public void setControlService(LauncherControlService controlService) {
        this.controlService = controlService;
    }

    public void handleGunInfo(GunInfo gunInfo) {
        if (controlService != null) {
            controlService.updateCurrentAngles(gunInfo.getPanAngle(), gunInfo.getTiltAngle());
        }

        double panDeg = Math.toDegrees(gunInfo.getPanAngle());
        double tiltDeg = Math.toDegrees(gunInfo.getTiltAngle());

        currentStatus.setPlatformAngle(panDeg);
        currentStatus.setCannonAngle(tiltDeg);
        currentStatus.setTimestamp(System.currentTimeMillis());

        boolean isAimed = (controlService != null) && controlService.isTargetAimed();
        currentStatus.setReadyToFire(currentStatus.evaluateReadyToFire() && isAimed);

        kafkaPublisher.publishTelemetry(currentStatus);
    }

    public void handleGunStatus(GunStatusInfo gunStatus) {
        if (gunStatus.getFault()) {
            logger.error("Gun Fault [ID: {}]: {}", gunStatus.getGunId(), gunStatus.getFaultText());
            currentStatus.setReportMessage("GUN_FAULT: " + gunStatus.getFaultText());
            currentStatus.setReadyToFire(false);
            kafkaPublisher.publishReports(currentStatus);
        }else {
            currentStatus.setReportMessage("OK");
            currentStatus.setReadyToFire(currentStatus.evaluateReadyToFire());
        }
    }

    public void handlePlatformPosition(PlatformPositionInfo platformPosition) {
        double rawX = platformPosition.getPositionX();
        double rawY = platformPosition.getPositionY();

        ownshipKalmanFilter.predict();
        ownshipKalmanFilter.update(rawX, rawY);

        double filteredX = ownshipKalmanFilter.getFilteredX();
        double filteredY = ownshipKalmanFilter.getFilteredY();

        logger.info("[OWNSHIP POS] Raw: [{}, {}] -> Filtered: [{}, {}]",
                rawX, rawY, String.format("%.14f", filteredX), String.format("%.14f", filteredY));

        currentStatus.setXCoordinate(filteredX);
        currentStatus.setYCoordinate(filteredY);
        currentStatus.setTimestamp(System.currentTimeMillis());


    }

    public void handleTargetPosition(TargetPositionInfo targetPosition) {
        double rawTargetX = targetPosition.getPositionX();
        double rawTargetY = targetPosition.getPositionY();

        targetKalmanFilter.predict();
        targetKalmanFilter.update(rawTargetX, rawTargetY);

        double filteredTargetX = targetKalmanFilter.getFilteredX();
        double filteredTargetY = targetKalmanFilter.getFilteredY();

        logger.info("[TARGET TRACK] Raw: [{}, {}] -> Kalman Filtered Target: [{}, {}]",
                rawTargetX, rawTargetY, String.format("%.14f", filteredTargetX), String.format("%.14f", filteredTargetY));

        if (controlService != null) {
            controlService.updateTargetPosition(filteredTargetX, filteredTargetY);
        }
    }

    public void handleHeartbeat(Heartbeat heartbeat) {
        currentStatus.setConnected(heartbeat.getHealthy());
        currentStatus.setAvailability(heartbeat.getState());
        currentStatus.setTimestamp(System.currentTimeMillis());

        kafkaPublisher.publishSystemStatus(currentStatus);
    }
}