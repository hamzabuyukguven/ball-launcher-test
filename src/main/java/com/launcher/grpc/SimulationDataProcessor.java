package com.launcher.grpc;

import com.heybeliada.grpc.GunInfo;
import com.heybeliada.grpc.GunStatusInfo;
import com.heybeliada.grpc.Heartbeat;
import com.heybeliada.grpc.PlatformPositionInfo;
import com.heybeliada.grpc.PlatformStatusInfo;
import com.heybeliada.grpc.StabilizationData;
import com.heybeliada.grpc.TargetPositionInfo;
import com.launcher.control.KalmanFilter;
import com.launcher.kafka.SystemStatusPublisher;
import com.launcher.kafka.model.SystemStatus;
import com.launcher.simulationtest.LauncherControlService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class SimulationDataProcessor {
    private static final Logger logger = LoggerFactory.getLogger(SimulationDataProcessor.class);

    private final KalmanFilter ownshipKalmanFilter = new KalmanFilter(0.1);
    private final KalmanFilter targetKalmanFilter = new KalmanFilter(0.1);
    private final SystemStatusPublisher kafkaPublisher;
    private final SystemStatus currentStatus = new SystemStatus();

    private LauncherControlService controlService;
    private double ownshipZ;

    public SimulationDataProcessor(SystemStatusPublisher kafkaPublisher) {
        this.kafkaPublisher = kafkaPublisher;
    }

    public synchronized void setControlService(LauncherControlService controlService) {
        this.controlService = controlService;
        currentStatus.setAmmoCount(controlService.getAmmoCount());
        currentStatus.setAmmoType(controlService.getAmmoType());
        refreshDerivedStatus();
    }

    public synchronized void handleGunInfo(GunInfo gunInfo) {
        if (controlService != null) {
            controlService.updateCurrentAngles(gunInfo.getPanAngle(), gunInfo.getTiltAngle());
        }
        currentStatus.setPlatformAngle(Math.toDegrees(gunInfo.getPanAngle()));
        currentStatus.setCannonAngle(Math.toDegrees(gunInfo.getTiltAngle()));
        refreshDerivedStatus();
        kafkaPublisher.publishTelemetry(snapshot());
    }

    public synchronized void handleGunStatus(GunStatusInfo gunStatus) {
        if (controlService != null) {
            controlService.updateGunStatus(
                    gunStatus.getReadyToFire(),
                    gunStatus.getFiring(),
                    gunStatus.getFault());
        }

        if (gunStatus.getFault()) {
            String faultText = gunStatus.getFaultText().isBlank()
                    ? "UNKNOWN_GUN_FAULT"
                    : gunStatus.getFaultText();
            currentStatus.setReportMessage("GUN_FAULT: " + faultText);
            logger.error("Gun fault [{}]: {}", gunStatus.getGunId(), faultText);
            refreshDerivedStatus();
            kafkaPublisher.publishReports(snapshot());
        } else {
            currentStatus.setReportMessage("OK");
            refreshDerivedStatus();
        }
        kafkaPublisher.publishSystemStatus(snapshot());
    }

    public synchronized void handlePlatformPosition(PlatformPositionInfo platformPosition) {
        double rawX = platformPosition.getPositionX();
        double rawY = platformPosition.getPositionY();
        ownshipZ = platformPosition.getPositionZ();

        ownshipKalmanFilter.predict();
        ownshipKalmanFilter.update(rawX, rawY);
        double filteredX = ownshipKalmanFilter.getFilteredX();
        double filteredY = ownshipKalmanFilter.getFilteredY();

        currentStatus.setXCoordinate(filteredX);
        currentStatus.setYCoordinate(filteredY);
        if (controlService != null) {
            controlService.updatePlatformPosition(filteredX, filteredY, ownshipZ);
        }
        refreshDerivedStatus();
        kafkaPublisher.publishTelemetry(snapshot());
    }

    public synchronized void handleTargetPosition(TargetPositionInfo targetPosition) {
        targetKalmanFilter.predict();
        targetKalmanFilter.update(targetPosition.getPositionX(), targetPosition.getPositionY());
        double filteredTargetX = targetKalmanFilter.getFilteredX();
        double filteredTargetY = targetKalmanFilter.getFilteredY();

        if (controlService != null) {
            controlService.updateTrackedTarget(
                    filteredTargetX,
                    filteredTargetY,
                    targetPosition.getPositionZ());
        }
    }

    public synchronized void handleStabilizationData(StabilizationData data) {
        if (controlService != null) {
            controlService.updatePlatformOrientation(data.getYaw());
        }
    }

    public synchronized void handlePlatformStatus(PlatformStatusInfo status) {
        if (controlService != null) {
            controlService.updateSimulationReady(status.getSimulationReady());
        }
        currentStatus.setConnected(status.getSimulationReady());
        refreshDerivedStatus();
        kafkaPublisher.publishSystemStatus(snapshot());
    }

    public synchronized void handleHeartbeat(Heartbeat heartbeat) {
        boolean healthy = heartbeat.getHealthy();
        currentStatus.setConnected(healthy);
        if (controlService != null) {
            controlService.updateSimulationReady(healthy);
        }
        if (!healthy) {
            currentStatus.setReportMessage("SIMULATION_HEARTBEAT_UNHEALTHY: " + heartbeat.getState());
            refreshDerivedStatus();
            kafkaPublisher.publishReports(snapshot());
        } else if (controlService == null || !controlService.isGunFault()) {
            currentStatus.setReportMessage("OK");
        }
        refreshDerivedStatus();
        kafkaPublisher.publishSystemStatus(snapshot());
    }

    public synchronized void publishHealthSnapshot(boolean grpcReady) {
        currentStatus.setConnected(grpcReady);
        refreshDerivedStatus();
        kafkaPublisher.publishSystemStatus(snapshot());
    }

    private void refreshDerivedStatus() {
        currentStatus.setTimestamp(System.currentTimeMillis());
        if (controlService != null) {
            currentStatus.setAmmoCount(controlService.getAmmoCount());
            currentStatus.setAmmoType(controlService.getAmmoType());
            currentStatus.setAimed(controlService.isTargetAimed());
            currentStatus.setReadyToFire(controlService.isReadyToFire());
            currentStatus.setAvailability(controlService.getAvailability());
        } else {
            currentStatus.setReadyToFire(false);
            currentStatus.setAvailability(currentStatus.isConnected() ? "IDLE" : "DISCONNECTED");
        }
    }

    private SystemStatus snapshot() {
        return new SystemStatus(currentStatus);
    }
}
