package com.hamza.balllauncherfrontend;

import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Scene;
import javafx.stage.Stage;

import java.io.IOException;

public class HelloApplication extends Application {
    private HelloController controller;

    @Override
    public void start(Stage stage) throws IOException {
        FXMLLoader loader = new FXMLLoader(HelloApplication.class.getResource("hello-view.fxml"));

        Scene scene = new Scene(loader.load(), 1180, 760);

        controller = loader.getController();

        stage.setTitle("Ball Launcher Control Panel");
        stage.setMinWidth(1000);
        stage.setMinHeight(680);
        stage.setScene(scene);
        stage.show();
    }

    @Override
    public void stop() {
        if (controller != null) {
            controller.shutdown();
        }
    }

    public static void main(String[] args) {
        launch();
    }
}

