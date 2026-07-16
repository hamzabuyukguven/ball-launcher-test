package com.launcher.kafka.model;

public class SystemStatus {
    private final boolean connected;
    private final String availability;
    private final double platformAngle;
    private final double cannonAngle;
    private long timeStamp;

    public SystemStatus(boolean connected, String availability, double platformAngle, double cannonAngle) {
        this.connected = connected;
        this.availability = availability;
        this.platformAngle = platformAngle;
        this.timeStamp = System.currentTimeMillis();
        this.cannonAngle = cannonAngle;
    }

    public boolean isConnected() {

        return connected;
    }

    public String getAvailability() {

        return availability;
    }

    public double getPlatformAngle() {
        return platformAngle;
    }

    public double getCannonAngle() {
        return cannonAngle;
    }
    public long getTimeStamp() {
        return timeStamp;
    }
}
