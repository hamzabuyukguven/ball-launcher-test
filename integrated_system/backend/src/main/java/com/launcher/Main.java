package com.launcher;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.CountDownLatch;

public final class Main {
    private static final Logger logger = LoggerFactory.getLogger(Main.class);

    private Main() {
    }

    public static void main(String[] args) {
        AppEngine engine = new AppEngine();
        CountDownLatch shutdownLatch = new CountDownLatch(1);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            engine.stop();
            shutdownLatch.countDown();
        }, "backend-shutdown"));

        try {
            engine.start();

            if (engine.getConfig().isConsoleFireEnabled()) {
                Thread consoleThread = new Thread(() -> readConsole(engine), "console-fire-input");
                consoleThread.setDaemon(true);
                consoleThread.start();
                logger.info("Console fire is enabled. Press ENTER to queue a shot.");
            }

            shutdownLatch.await();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            engine.stop();
        } catch (Exception e) {
            logger.error("Backend startup failed", e);
            engine.stop();
            System.exit(1);
        }
    }

    private static void readConsole(AppEngine engine) {
        try {
            while (System.in.read() != -1) {
                engine.getControlService().fire();
            }
        } catch (Exception e) {
            logger.warn("Console input stopped: {}", e.getMessage());
        }
    }
}
