package com.hamza.balllauncherfrontend.kafka;

public class LauncherTelemetry {

    private double targetX;
    private double targetY;

    public LauncherTelemetry() {
    }

    public LauncherTelemetry(double targetX, double targetY) {
        this.targetX = targetX;
        this.targetY = targetY;
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
}
