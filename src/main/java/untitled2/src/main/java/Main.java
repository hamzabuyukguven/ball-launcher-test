import com.launcher.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


public class Main {
    private static final Logger logger = LoggerFactory.getLogger(Main.class);


    public static void main(String[] args) {

        logger.info("System starting...");

        AppEngine engine = new AppEngine();

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("System shutting down...");
            engine.stop();
        }));

        try {
            engine.start();
            while (true){
                Thread.sleep(1000);
            }
        }
        catch (InterruptedException e) {
            logger.error("Main thread was interrupted unexpectedly.", e);
            engine.stop();
        }

    }
}