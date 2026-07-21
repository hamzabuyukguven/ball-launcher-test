package com.launcher;

import com.launcher.kafka.model.SystemStatus;
import com.launcher.tcp.TCPLauncher;
import com.launcher.kafka.SystemStatusPublisher;
import org.slf4j.LoggerFactory;
import org.slf4j.Logger;


public class HeartbeatManager implements Runnable{

        private static final Logger logger = LoggerFactory.getLogger(HeartbeatManager.class);
        private final TCPLauncher tcpLauncher;
        private final SystemStatusPublisher statusPublisher;
        private final int intervalMillis = 5000;
        private volatile boolean running = true;
        private Thread workerThread;


        public HeartbeatManager(TCPLauncher tcpLauncher, SystemStatusPublisher statusPublisher){
            this.tcpLauncher = tcpLauncher;
            this.statusPublisher = statusPublisher;
        }


        @Override
        public void run() {
            logger.info("System health monitoring started.");
            while (running && !Thread.currentThread().isInterrupted()) {
                try {
                    Thread.sleep(intervalMillis);
                    checkSystemHealth();
                } catch (InterruptedException e) {
                    logger.info("System health monitoring thread was interrupted.");
                    running = false;
                }
            }
        }
        private void checkSystemHealth() {
            boolean isTcpAlive = tcpLauncher.isActive();

            logger.info("TCP Server Status: " + (isTcpAlive ? "ACTIVE" : "INACTIVE"));
            SystemStatus status = new SystemStatus(isTcpAlive, isTcpAlive ? "ACTIVE" : "INACTIVE", 0.0, 0.0, System.currentTimeMillis());
            if (statusPublisher != null) {
                statusPublisher.publishStatus(status);
            }

        }
        public void start() {
            logger.info("Starting system health monitoring system...");
            running = true;
            workerThread = new Thread(this, "Heartbeat-worker-thread");
            workerThread.start();
        }

        public void stop() {
            logger.info("Stopping system health monitoring system...");
            running = false;
            if(workerThread != null) {
                workerThread.interrupt();
            }
        }
}
