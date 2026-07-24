package com.launcher.simulationtest;

import com.launcher.grpc.NavalBridgeGrpcClient;
import com.launcher.grpc.SimulationDataProcessor;
import com.launcher.kafka.SystemStatusPublisher;
import com.launcher.kafka.model.LauncherTelemetry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class DirectTestMain {

    private static final Logger logger = LoggerFactory.getLogger(DirectTestMain.class);

    public static void main(String[] args) {

        try {
            SystemStatusPublisher kafkaPublisher = new SystemStatusPublisher();
            SimulationDataProcessor dataProcessor = new SimulationDataProcessor(kafkaPublisher);
            NavalBridgeGrpcClient grpcClient = new NavalBridgeGrpcClient("10.30.200.195", 50052, dataProcessor);

            grpcClient.startStreaming("test_client_01");
            logger.info("gRPC streams started, connected to simulator.");

            LauncherControlService controlService = new LauncherControlService(grpcClient);
            dataProcessor.setControlService(controlService);

            Thread.sleep(2000);

            LauncherTelemetry testTarget = new LauncherTelemetry(1000.0, 500.0);
            logger.info("Setting Target Coordinates -> X: {}, Y: {}", testTarget.getTargetX(), testTarget.getTargetY());

            controlService.processTargetTelemetry(testTarget);

            Thread.sleep(5000);
            logger.info("ISSUING FIRE COMMAND...");
            controlService.fire();

            Thread.sleep(10000);

            grpcClient.shutdown();
            logger.info("Test completed successfully, gRPC channel closed.");

        } catch (Exception e) {
            logger.error("An error occurred during test execution: ", e);
        }
    }
}