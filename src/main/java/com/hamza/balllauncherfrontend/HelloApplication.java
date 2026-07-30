package com.hamza.balllauncherfrontend;

import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.geometry.Rectangle2D;
import javafx.scene.Scene;
import javafx.stage.Screen;
import javafx.stage.Stage;

import java.io.IOException;

public class HelloApplication extends Application {

    private HelloController controller;

    @Override
    public void start(Stage stage) throws IOException {
        FXMLLoader loader = new FXMLLoader(HelloApplication.class.getResource("hello-view.fxml"));

        Rectangle2D screen = Screen.getPrimary().getVisualBounds();
        double width = Math.min(840, screen.getWidth() - 40);
        double height = Math.min(900, screen.getHeight() - 40);

        Scene scene = new Scene(loader.load(), width, height);
        controller = loader.getController();

        stage.setTitle("Gun Launcher Control Panel");
        stage.setScene(scene);
        stage.setMinWidth(700);
        stage.setMinHeight(500);
        stage.setX(screen.getMinX() + (screen.getWidth() - width) / 2);
        stage.setY(screen.getMinY() + Math.max(0, (screen.getHeight() - height) / 2));
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
