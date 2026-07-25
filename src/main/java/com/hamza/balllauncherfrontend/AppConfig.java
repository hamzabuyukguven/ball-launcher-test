package com.hamza.balllauncherfrontend;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

public class AppConfig {

    private static final Logger logger = LoggerFactory.getLogger(AppConfig.class);
    private static final Properties properties = new Properties();

    static {
        try (InputStream input = AppConfig.class.getResourceAsStream("config.properties")) {
            if (input != null) {
                properties.load(input);
                logger.info("Configuration loaded from config.properties");
            } else {
                logger.warn("config.properties not found, using defaults.");
            }
        } catch (IOException e) {
            logger.error("Failed to load config.properties", e);
        }
    }

    public static String getKafkaBootstrapServers() {
        String envOverride = System.getenv("KAFKA_BOOTSTRAP_SERVERS");
        if (envOverride != null && !envOverride.isBlank()) {
            return envOverride;
        }
        return properties.getProperty("kafka.bootstrap.servers", "localhost:9092");
    }
}
