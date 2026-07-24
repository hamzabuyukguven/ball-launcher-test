package com.launcher;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Main {
    private static final Logger logger = LoggerFactory.getLogger(Main.class);

    public static void main(String[] args) {

        AppEngine engine = new AppEngine();

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("System shutdown signal received, terminating services...");
            engine.stop();
        }));

        try {
            engine.start();
            logger.info("All services active. gRPC streams and Kafka listeners are running.");
            logger.info("Press [ENTER] to fire.");

            while (true) {
                int readByte = System.in.read();
                if (readByte == '\n') {
                    logger.info("FIRE COMMAND ISSUED!");
                    engine.getControlService().fire();
                }
            }

        } catch (Exception e) {
            logger.error("Main thread was unexpectedly interrupted.", e);
            engine.stop();
        }
    }
}