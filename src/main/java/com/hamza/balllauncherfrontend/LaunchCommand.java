package com.hamza.balllauncherfrontend;

public class LaunchCommand {

    private String action;      // "FIRE", "STOW", "EMERGENCY_STOP", "SET_POSITION"
    private double targetX;
    private double targetY;

    public LaunchCommand() {
        // Jackson için boş constructor
    }

    public LaunchCommand(String action, double targetX, double targetY) {
        this.action = action;
        this.targetX = targetX;
        this.targetY = targetY;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
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
