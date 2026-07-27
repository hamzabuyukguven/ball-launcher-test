package com.hamza.balllauncherfrontend.kafka;

public class LauncherTelemetry {

    private double targetX;
    private double targetY;
    private double targetZ;

    public LauncherTelemetry() {
    }


    public LauncherTelemetry(double targetX, double targetY) {
        this.targetX = targetX;
        this.targetY = targetY;
        this.targetZ = 0.0;
    }

    public LauncherTelemetry(double targetX, double targetY, double targetZ) {
        this.targetX = targetX;
        this.targetY = targetY;
        this.targetZ = targetZ;
    }

    public double getTargetX() {
        return targetX;
    }

    public void setTargetX(double targetX) {
        this.targetX = targetX;
    }

    public double getTargetY() {
        return targetY;
    }

    public void setTargetY(double targetY) {
        this.targetY = targetY;
    }

    public double getTargetZ() {
        return targetZ;
    }

    public void setTargetZ(double targetZ) {
        this.targetZ = targetZ;
    }
}

