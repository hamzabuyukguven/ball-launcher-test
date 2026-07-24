package com.hamza.balllauncherfrontend;

import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Scene;
import javafx.stage.Stage;
import com.hamza.balllauncherfrontend.kafka.SystemStatusConsumer;
import com.hamza.balllauncherfrontend.HelloController;

import java.io.IOException;

public class HelloApplication extends Application {
@Override
public void start(Stage stage) throws IOException {
    FXMLLoader fxmlLoader = new FXMLLoader(HelloApplication.class.getResource("hello-view.fxml"));
    Scene scene = new Scene(fxmlLoader.load(), 730, 850);

    HelloController controller = fxmlLoader.getController();

    stage.setTitle("Ball Launcher Control Panel");
    stage.setScene(scene);

    stage.setOnCloseRequest(event -> {
        if (controller != null) {
            controller.shutdown();
        }
    });

    stage.show();
}
}
