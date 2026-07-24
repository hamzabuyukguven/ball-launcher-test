package com.launcher.simulationtest;

import com.launcher.control.PIDController;
import com.launcher.grpc.NavalBridgeGrpcClient;
import com.launcher.kafka.model.LauncherTelemetry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LauncherControlService {

    private static final Logger logger = LoggerFactory.getLogger(LauncherControlService.class);

    private final NavalBridgeGrpcClient grpcClient;
    private final PIDController panPid;
    private final PIDController tiltPid;

    private volatile double currentPanRad = 0.0;
    private volatile double currentTiltRad = 0.0;

    private volatile double targetX = 0.0;
    private volatile double targetY = 0.0;

    private long lastCalcTimeMs = 0;

    public LauncherControlService(NavalBridgeGrpcClient grpcClient) {
        this.grpcClient = grpcClient;

        this.panPid = new PIDController(2.5, 0.1, 0.5, -1.0, 1.0);
        this.tiltPid = new PIDController(2.5, 0.1, 0.5, -1.0, 1.0);
    }

    public void updateCurrentAngles(double panRad, double tiltRad) {
        this.currentPanRad = panRad;
        this.currentTiltRad = tiltRad;
    }

    public void updateTargetPosition(double targetX, double targetY) {
        this.targetX = targetX;
        this.targetY = targetY;

        long currentTimeMs = System.currentTimeMillis();
        double dt = 0.1;
        if (lastCalcTimeMs > 0) {
            dt = (currentTimeMs - lastCalcTimeMs) / 1000.0;
        }
        lastCalcTimeMs = currentTimeMs;

        double targetPanRad = Math.atan2(targetY, targetX);
        double targetTiltRad = 0.0;

        double commandedPanRate = panPid.calculate(targetPanRad, currentPanRad, dt);
        double commandedTiltRate = tiltPid.calculate(targetTiltRad, currentTiltRad, dt);

        grpcClient.sendGunRateCommand(commandedPanRate, commandedTiltRate);
    }

    public void processTargetTelemetry(LauncherTelemetry target) {
        if (target != null) {
            updateTargetPosition(target.getTargetX(), target.getTargetY());
        }
    }

    public boolean isTargetAimed() {
        double targetPanRad = Math.atan2(targetY, targetX);
        double errorRad = Math.abs(targetPanRad - currentPanRad);

        return errorRad < 0.017;
    }

    public void fire() {
        double muzzleVelocity = 60.0;
        logger.info("(Muzzle Velocity: {} m/s)...", muzzleVelocity);
        grpcClient.sendFireCommand(muzzleVelocity);
    }

    public void emergencyStop(){
        logger.warn("!!! EMERGENCY STOP !!!");
        grpcClient.sendGunRateCommand(0.0,0.0);
    }

    public void moveToStowPosition(){
        logger.info("Moving to Stow Position...");
        this.targetX = 0.0;
        this.targetY = 0.0;

        double commandedPanRate = panPid.calculate(0.0, currentPanRad, 0.1);
        double commandedTiltRate =  tiltPid.calculate(0.0, currentTiltRad, 0.1);
        grpcClient.sendGunRateCommand(commandedPanRate, commandedTiltRate);
    }

}