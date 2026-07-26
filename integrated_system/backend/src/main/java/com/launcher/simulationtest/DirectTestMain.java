package com.launcher.simulationtest;

import com.launcher.AppEngine;
import com.launcher.kafka.model.LauncherTelemetry;

public final class DirectTestMain {
    private DirectTestMain() {
    }

    public static void main(String[] args) throws Exception {
        AppEngine engine = new AppEngine();
        Runtime.getRuntime().addShutdownHook(new Thread(engine::stop));
        engine.start();

        LauncherTelemetry target = new LauncherTelemetry(1000.0, 500.0, 0.0);
        engine.getControlService().requestFire(target);

        Thread.currentThread().join();
    }
}
