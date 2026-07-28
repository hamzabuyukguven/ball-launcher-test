package com.launcher.control;

public class PIDController {
    private final double kp;
    private final double ki;
    private final double kd;

    private double integralSum = 0.0;
    private double lastError = 0.0;
    private boolean isFirstRun = true;

    private final double minOutput;
    private final double maxOutput;

    public PIDController(double kp, double ki, double kd, double minOutput, double maxOutput) {
        this.kp = kp;
        this.ki = ki;
        this.kd = kd;
        this.minOutput = minOutput;
        this.maxOutput = maxOutput;
    }

    public double calculate(double setpoint, double actual, double dt){
        if(dt <= 0.0){
            return 0.0;
        }

        double error = setpoint - actual; 
        double pTerm = kp * error;

        double iTerm = 0.0;
        if(ki != 0.0){
            integralSum += error * dt;
            iTerm = ki * integralSum;

            if (iTerm > maxOutput){
                iTerm = maxOutput;
                integralSum = maxOutput / ki;
            }
            else if (iTerm < minOutput){
                iTerm = minOutput;
                integralSum = minOutput / ki;
            }
        } else {
            integralSum = 0.0;
            iTerm = 0.0;
        }

        double dTerm = 0.0;
        if(!isFirstRun){
            double errorDerivative = (error - lastError) / dt;
            dTerm = kd * errorDerivative;
        }
        else {
            isFirstRun = false;
        }
        lastError = error;

        double output = pTerm + iTerm + dTerm;

        if(output > maxOutput){
            output = maxOutput;
        }
        else if (output < minOutput){
            output = minOutput;
        }
        return output;
    }

    public void reset(){
        this.integralSum = 0.0;
        this.lastError = 0.0;
        this.isFirstRun = true;
    }
}