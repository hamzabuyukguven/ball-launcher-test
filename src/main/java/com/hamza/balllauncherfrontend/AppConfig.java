package com.hamza.balllauncherfrontend;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

public final class AppConfig {

    private static final Logger logger = LoggerFactory.getLogger(AppConfig.class);
    private static final Properties PROPERTIES = new Properties();

    static {
        try (InputStream input = AppConfig.class.getResourceAsStream("config.properties")) {
            if (input != null) {
                PROPERTIES.load(input);
                logger.info("Configuration loaded from config.properties");
            } else {
                logger.warn("config.properties not found; defaults will be used");
            }
        } catch (Exception e) {
            logger.error("Could not load frontend configuration", e);
        }
    }

    private AppConfig() {
    }

    private static String value(String propertyName, String envName, String defaultValue) {
        String env = System.getenv(envName);
        if (env != null && !env.isBlank()) return env.trim();
        return PROPERTIES.getProperty(propertyName, defaultValue).trim();
    }

    public static String getKafkaBootstrapServers() {
        return value("kafka.bootstrap.servers", "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092");
    }

    public static int getReportsMaxLines() {
        try {
            return Integer.parseInt(PROPERTIES.getProperty("reports.max.lines", "200"));
        } catch (NumberFormatException e) {
            return 200;
        }
    }

    public static double getDefaultMuzzleVelocity() {
        try {
            return Double.parseDouble(PROPERTIES.getProperty("ballistics.muzzle.velocity", "60.0"));
        } catch (NumberFormatException e) {
            return 60.0;
        }
    }

    public static List<double[]> getForbiddenSectors() {
        List<double[]> sectors = new ArrayList<>();
        String raw = value("forbidden.sectors", "FORBIDDEN_SECTORS", "");
        if (raw.isBlank()) return sectors;

        for (String part : raw.split(",")) {
            String[] bounds = part.trim().split(":");
            if (bounds.length != 2) {
                logger.warn("Invalid forbidden sector definition: {}", part);
                continue;
            }
            try {
                sectors.add(new double[]{
                        Double.parseDouble(bounds[0].trim()),
                        Double.parseDouble(bounds[1].trim())
                });
            } catch (NumberFormatException e) {
                logger.warn("Invalid forbidden sector numbers: {}", part);
            }
        }
        return sectors;
    }

    public static String commandTopic() {
        return value("kafka.command.topic", "KAFKA_COMMAND_TOPIC", "launcher.commands");
    }

    public static String statusTopic() {
        return value("kafka.status.topic", "KAFKA_STATUS_TOPIC", "launcher.status");
    }

    public static String telemetryTopic() {
        return value("kafka.telemetry.topic", "KAFKA_TELEMETRY_TOPIC", "launcher.telemetry");
    }

    public static String reportsTopic() {
        return value("kafka.reports.topic", "KAFKA_REPORTS_TOPIC", "launcher.reports");
    }

    public static String statusGroupId() {
        return value("kafka.status.group.id", "KAFKA_STATUS_GROUP_ID", "launcher-frontend-status");
    }

    public static String reportsGroupId() {
        return value("kafka.reports.group.id", "KAFKA_REPORTS_GROUP_ID", "launcher-frontend-reports");
    }
}
