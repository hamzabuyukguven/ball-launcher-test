package com.launcher.tcp;

import org.slf4j.LoggerFactory;
import org.slf4j.Logger;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;


public class TCPServer implements Runnable{

    private static final Logger logger = LoggerFactory.getLogger(TCPServer.class);
    private final int port;

    public TCPServer(int port){
        this.port = port;
    }
    @Override
    public void run() {
        logger.info("Connecting to TCP Server... Port: " + port);

        try (ServerSocket serverSocket = new ServerSocket(port)){
            while (true){
                logger.info("Waiting for connection..." );
                Socket socket = serverSocket.accept();
                logger.info("Client connected.");

                try(
                        BufferedReader input = new BufferedReader(new InputStreamReader(socket.getInputStream()));
                        PrintWriter output = new PrintWriter(socket.getOutputStream(), true)
                ){

                    String message = input.readLine();
                    System.out.println("Incoming data: " + message);
                    output.println("Message taken.");
                }

            }
        } catch (Exception e){
            System.out.println("Warning!" +  e.getMessage());
        }
    }
}
