/*
package com.launcher.grpc;

import com.launcher.config.AppConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class TCPLauncher {

    private static final Logger logger = LoggerFactory.getLogger(TCPLauncher.class);
    private Thread tcpThread;
    private final AppConfig config;
    private volatile boolean isActive = false;

    public TCPLauncher(AppConfig config) {
        this.config = config;
    }
    public void start () {
        int port = config.getTcpPort();
        logger.info("Port configuration received: " + port);

        TCPServer server = new TCPServer(port);

        tcpThread = new Thread(server);
        this.tcpThread.setName("TCPLauncher");
        this.isActive = true;
        this.tcpThread.start();
    }


    public void stop(){
        logger.info("Disconnecting from TCP server...");
        this.isActive = false;
        if ( tcpThread != null) {
            tcpThread.interrupt();
            tcpThread = null;
        }
    }
    public boolean isActive() {
        return this.isActive;
    }

}
*/