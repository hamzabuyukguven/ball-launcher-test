module com.hamza.balllauncherfrontend {
    requires javafx.controls;
    requires javafx.fxml;
    requires kafka.clients;
    requires org.slf4j;
    requires com.fasterxml.jackson.core;
    requires com.fasterxml.jackson.databind;
    opens com.hamza.balllauncherfrontend.kafka to com.fasterxml.jackson.databind;

    opens com.hamza.balllauncherfrontend to javafx.fxml;
    exports com.hamza.balllauncherfrontend;
    exports com.hamza.balllauncherfrontend.kafka;
}
