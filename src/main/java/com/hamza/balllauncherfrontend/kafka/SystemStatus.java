package com.hamza.balllauncherfrontend.kafka;

public class SystemStatus {

    private boolean connected;
    private String availability;
    private double platformAngle;
    private double cannonAngle;
    private long timeStamp;

    public SystemStatus() {
    }

    public boolean isConnected() {
        return connected;
    }

    public void setConnected(boolean connected) {
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
        return timeStamp;
    }

    public void setTimeStamp(long timeStamp) {
        this.timeStamp = timeStamp;
    }
}
