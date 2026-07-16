package com.launcher.config;

import java.io.InputStream;
import java.util.Properties;

public class AppConfig {
    private int tcpPort = 100;
    private String kafkaBootstrapServers = "localhost:9092";
    private String kafkaTopicName = "launcher-events";

    public AppConfig() {
        Properties prop = new Properties();

        try (InputStream input = getClass().getClassLoader().getResourceAsStream("config.properties")) {
            if (input != null) {
                prop.load(input);
                String portStr = prop.getProperty("launcher.tcp.port");
                if (portStr != null) {
                    this.tcpPort = Integer.parseInt(portStr.trim());
                }

                String kafkaServers = prop.getProperty("launcher.kafka.bootstrap.servers");
                if (kafkaServers != null) {
                    this.kafkaBootstrapServers = kafkaServers.trim();
                }
                String kafkaTopicStr = prop.getProperty("launcher.kafka.topic");
                if (kafkaTopicStr != null) {
                    this.kafkaTopicName = kafkaTopicStr.trim();
                }

            } else {
                System.out.println("config.properties not found: " + tcpPort);
            }
        } catch (Exception e) {
            System.out.println("Error loading configuration: " + e.getMessage());
        }
    }

    public int getTcpPort() {

        return tcpPort;
    }


    public String getKafkaBootstrapServers() {
        return kafkaBootstrapServers;
    }

    public String getKafkaTopicName() {
        return kafkaTopicName;
    }
}