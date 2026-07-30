package com.hamza.balllauncherfrontend.kafka;

public class LaunchCommand {

    private LauncherAction action;
    private LauncherTelemetry telemetry;

    public LaunchCommand() {
    }

    public LaunchCommand(LauncherAction action, LauncherTelemetry telemetry) {
        this.action = action;
        this.telemetry = telemetry;
    }

    public LauncherAction getAction() {
        return action;
    }

    public void setAction(LauncherAction action) {
        this.action = action;
    }

    public LauncherTelemetry getTelemetry() {
        return telemetry;
    }

    public void setTelemetry(LauncherTelemetry telemetry) {
        this.telemetry = telemetry;
    }
}
