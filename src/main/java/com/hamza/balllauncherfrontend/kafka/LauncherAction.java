package com.hamza.balllauncherfrontend.kafka;

public enum LauncherAction {
    SET_MANUAL_TARGET,
    USE_TRACKED_TARGET,
    FIRE,
    STOW,
    EMERGENCY_STOP,
    CLEAR_EMERGENCY_STOP;

    @Override
    public String toString() {
        return name();
    }
}
