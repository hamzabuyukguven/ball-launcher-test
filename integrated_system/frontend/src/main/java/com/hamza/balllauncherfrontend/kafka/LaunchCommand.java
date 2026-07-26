package com.hamza.balllauncherfrontend.kafka;

public class LaunchCommand {
    private String action;
    private LauncherTelemetry telemetry;

    public LaunchCommand() {
    }

    public LaunchCommand(LauncherAction action, LauncherTelemetry telemetry) {
        this.action = action.name();
        this.telemetry = telemetry;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public LauncherTelemetry getTelemetry() {
        return telemetry;
    }

    public void setTelemetry(LauncherTelemetry telemetry) {
        this.telemetry = telemetry;
    }
}
