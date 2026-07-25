package com.hamza.balllauncherfrontend.kafka;

public enum LauncherAction {
    FIRE,
    STOW,
    EMERGENCY_STOP,
    SET_MANUAL_TARGET;

    @Override
    public String toString() {
        return name();
    }
}