module com.hamza.balllauncherfrontend {
    requires javafx.controls;
    requires javafx.fxml;
    requires kafka.clients;
    requires org.slf4j;


    opens com.hamza.balllauncherfrontend to javafx.fxml;
    exports com.hamza.balllauncherfrontend;
}