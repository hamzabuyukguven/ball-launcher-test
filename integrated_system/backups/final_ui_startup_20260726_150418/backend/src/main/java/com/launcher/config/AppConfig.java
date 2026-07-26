package com.launcher.config;

import java.io.InputStream;
import java.util.Properties;

public final class AppConfig {
    private final Properties properties = new Properties();

    public AppConfig() {
        try (InputStream input = getClass().getClassLoader().getResourceAsStream("config.properties")) {
            if (input != null) {
                properties.load(input);
            }
        } catch (Exception e) {
            throw new IllegalStateException("config.properties could not be loaded", e);
        }
    }

    private String value(String propertyName, String envName, String defaultValue) {
        String env = System.getenv(envName);
        if (env != null && !env.isBlank()) {
            return env.trim();
        }
        return properties.getProperty(propertyName, defaultValue).trim();
    }

    private int intValue(String propertyName, String envName, int defaultValue) {
        return Integer.parseInt(value(propertyName, envName, Integer.toString(defaultValue)));
    }

    private double doubleValue(String propertyName, String envName, double defaultValue) {
        return Double.parseDouble(value(propertyName, envName, Double.toString(defaultValue)));
    }

    private boolean booleanValue(String propertyName, String envName, boolean defaultValue) {
        return Boolean.parseBoolean(value(propertyName, envName, Boolean.toString(defaultValue)));
    }

    public String getKafkaBootstrapServers() {
        return value("kafka.bootstrap.servers", "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092");
    }

    public String getKafkaCommandTopic() {
        return value("kafka.command.topic", "KAFKA_COMMAND_TOPIC", "launcher.commands");
    }

    public String getKafkaStatusTopic() {
        return value("kafka.status.topic", "KAFKA_STATUS_TOPIC", "launcher.status");
    }

    public String getKafkaTelemetryTopic() {
        return value("kafka.telemetry.topic", "KAFKA_TELEMETRY_TOPIC", "launcher.telemetry");
    }

    public String getKafkaReportsTopic() {
        return value("kafka.reports.topic", "KAFKA_REPORTS_TOPIC", "launcher.reports");
    }

    public String getKafkaConsumerGroupId() {
        return value("kafka.command.group.id", "KAFKA_COMMAND_GROUP_ID", "launcher-backend");
    }

    public String getGrpcHost() {
        return value("simulation.grpc.host", "SIMULATION_GRPC_HOST", "127.0.0.1");
    }

    public int getGrpcPort() {
        return intValue("simulation.grpc.port", "SIMULATION_GRPC_PORT", 50052);
    }

    public String getGrpcClientId() {
        return value("simulation.grpc.client.id", "SIMULATION_GRPC_CLIENT_ID", "launcher-backend");
    }

    public int getGrpcDeadlineMillis() {
        return intValue("simulation.grpc.deadline.ms", "SIMULATION_GRPC_DEADLINE_MS", 2500);
    }

    public boolean isBackendControlEnabled() {
        return booleanValue("control.enabled", "CONTROL_ENABLED", true);
    }

    public double getControlRateHz() {
        return doubleValue("control.rate.hz", "CONTROL_RATE_HZ", 20.0);
    }

    public double getMuzzleVelocity() {
        return doubleValue("control.muzzle.velocity", "MUZZLE_VELOCITY", 18.0);
    }

    public int getFireRetryIntervalMillis() {
        return intValue("control.fire.retry.interval.ms", "FIRE_RETRY_INTERVAL_MS", 1000);
    }

    public double getMaxPanRate() {
        return doubleValue("control.max.pan.rate", "MAX_PAN_RATE", 1.0);
    }

    public double getMaxTiltRate() {
        return doubleValue("control.max.tilt.rate", "MAX_TILT_RATE", 1.0);
    }

    public double getAimToleranceRad() {
        return Math.toRadians(doubleValue("control.aim.tolerance.deg", "AIM_TOLERANCE_DEG", 1.0));
    }

    public double getPanKp() {
        return doubleValue("control.pan.kp", "PAN_KP", 2.5);
    }

    public double getPanKi() {
        return doubleValue("control.pan.ki", "PAN_KI", 0.1);
    }

    public double getPanKd() {
        return doubleValue("control.pan.kd", "PAN_KD", 0.5);
    }

    public double getTiltKp() {
        return doubleValue("control.tilt.kp", "TILT_KP", 2.5);
    }

    public double getTiltKi() {
        return doubleValue("control.tilt.ki", "TILT_KI", 0.1);
    }

    public double getTiltKd() {
        return doubleValue("control.tilt.kd", "TILT_KD", 0.5);
    }

    public int getInitialAmmoCount() {
        return intValue("ammo.initial.count", "AMMO_INITIAL_COUNT", 200);
    }

    public String getAmmoType() {
        return value("ammo.type", "AMMO_TYPE", "76MM");
    }

    public int getHeartbeatPublishIntervalMillis() {
        return intValue("heartbeat.publish.interval.ms", "HEARTBEAT_PUBLISH_INTERVAL_MS", 1000);
    }

    public boolean isConsoleFireEnabled() {
        return booleanValue("console.fire.enabled", "CONSOLE_FIRE_ENABLED", false);
    }
}
