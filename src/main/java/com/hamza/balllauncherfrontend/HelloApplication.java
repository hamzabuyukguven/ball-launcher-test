package com.hamza.balllauncherfrontend;

import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Scene;
import javafx.stage.Stage;
import com.hamza.balllauncherfrontend.kafka.SystemStatusConsumer;

import java.io.IOException;

public class HelloApplication extends Application {
    @Override
    public void start(Stage stage) throws IOException {
        FXMLLoader fxmlLoader = new FXMLLoader(HelloApplication.class.getResource("hello-view.fxml"));
        Scene scene = new Scene(fxmlLoader.load(), 320, 240);
        stage.setTitle("Hello!");
        stage.setScene(scene);
        stage.show();

        Thread consumerThread = new Thread(new SystemStatusConsumer("10.152.220.16:9092", "launcher-group", message ->{
            System.out.println("gelen mesaj:" +message);
        }));
        consumerThread.setDaemon(true);
        consumerThread.start();

    }
}
