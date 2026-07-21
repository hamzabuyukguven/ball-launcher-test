package com.hamza.balllauncherfrontend.kafka;

public class LaunchCommand {

    private String action;

    public LaunchCommand() {
    }

    public LaunchCommand(String action) {
        this.action = action;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }
}
