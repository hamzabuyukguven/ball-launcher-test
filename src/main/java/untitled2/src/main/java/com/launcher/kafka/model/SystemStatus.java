package com.launcher.kafka.model;

public class SystemStatus {
    private boolean connected;
    private String availability;
    private double platformAngle;
    private double cannonAngle;
    private long timestamp;
    private double xCoordinate;
    private double yCoordinate;
    private int ammoCount;
    private String ammoType;
    private String reportMessage;

    public SystemStatus() {
    }

    public SystemStatus(boolean connected, String availability, double platformAngle, double cannonAngle, long timestamp) {
        this.connected = connected;
        this.availability = availability;
        this.platformAngle = platformAngle;
        this.timestamp = timestamp;
        this.cannonAngle = cannonAngle;
    }

    public boolean isConnected() {
        return connected;
    }
    public void setConnected(boolean connected){
        this.connected = connected;
    }

    public String getAvailability() {

        return availability;
    }
    public void setAvailability(String availability) {

        this.availability = availability;
    }

    public double getPlatformAngle() {
        return platformAngle;
    }
    public void setPlatformAngle(double platformAngle) {
        this.platformAngle = platformAngle;
    }

    public double getCannonAngle() {
        return cannonAngle;
    }
    public void setCannonAngle(double cannonAngle) {
        this.cannonAngle = cannonAngle;
    }
    public long getTimeStamp() {
        return timestamp;
    }
    public void setTimeStamp(long timeStamp) {
        this.timestamp = timestamp;
    }
}
