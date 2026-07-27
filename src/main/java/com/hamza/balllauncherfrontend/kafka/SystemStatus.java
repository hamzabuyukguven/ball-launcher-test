package com.hamza.balllauncherfrontend.kafka;

public class SystemStatus {

    private boolean connected;
    private String availability = "DISCONNECTED";
    private double platformAngle;
    private double cannonAngle;
    private long timestamp;
    private double xCoordinate;
    private double yCoordinate;
    private int ammoCount;
    private String ammoType;
    private String reportMessage = "OK";

    private boolean aimed;

    private boolean readyToFire;

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

    public long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

    public double getXCoordinate() {
        return xCoordinate;
    }

    public void setXCoordinate(double xCoordinate) {
        this.xCoordinate = xCoordinate;
    }

    public double getYCoordinate() {
        return yCoordinate;
    }

    public void setYCoordinate(double yCoordinate) {
        this.yCoordinate = yCoordinate;
    }

    public int getAmmoCount() {
        return ammoCount;
    }

    public void setAmmoCount(int ammoCount) {
        this.ammoCount = ammoCount;
    }

    public String getAmmoType() {
        return ammoType;
    }

    public void setAmmoType(String ammoType) {
        this.ammoType = ammoType;
    }

    public String getReportMessage() {
        return reportMessage;
    }

    public void setReportMessage(String reportMessage) {
        this.reportMessage = reportMessage;
    }

    public boolean isAimed() {
        return aimed;
    }

    public void setAimed(boolean aimed) {
        this.aimed = aimed;
    }

    public boolean isReadyToFire() {
        return readyToFire;
    }

    public void setReadyToFire(boolean readyToFire) {
        this.readyToFire = readyToFire;
    }
}

