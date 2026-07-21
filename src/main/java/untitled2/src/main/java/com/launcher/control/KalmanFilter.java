package com.launcher.control;

import org.ejml.data.DMatrixRMaj;
import org.ejml.dense.row.CommonOps_DDRM;
import org.ejml.dense.row.factory.LinearSolverFactory_DDRM;
import org.ejml.interfaces.linsol.LinearSolverDense;

public class KalmanFilter {

    private DMatrixRMaj x; //Durum Vektörü olacak[X,Y,Vx,Vy]
    private DMatrixRMaj P; //Kovaryans Matrisi
    private DMatrixRMaj F; //Durum geçiş matrisi
    private DMatrixRMaj Q; //Gürültü matrisi
    private DMatrixRMaj H; //Ölçüm matrisi
    private DMatrixRMaj R; //Ölçüm gürültü matrisi
    private final double dt;

    public KalmanFilter(double timeStep) {
        this.dt = timeStep;
        x = new DMatrixRMaj(4, 1);

        P = new DMatrixRMaj(4, 4);
        CommonOps_DDRM.setIdentity(P);
        CommonOps_DDRM.scale(100.0, P);

        F = new DMatrixRMaj(new double[][]{
                {1, 0, dt, 0},
                {0, 1, 0, dt},
                {0, 0, 1, 0},
                {0, 0, 0, 1}
        });

        H = new DMatrixRMaj(new double[][]{
                {1, 0, 0, 0},
                {0, 1, 0, 0}
        });

        Q = new DMatrixRMaj(4, 4);
        CommonOps_DDRM.setIdentity(Q);
        CommonOps_DDRM.scale(0.05, Q);

        R = new DMatrixRMaj(new double[][]{
                {0.1, 0},
                {0, 0.1}
        });
    }


    public void predict(){
        DMatrixRMaj xNext = new DMatrixRMaj(4, 1);
        CommonOps_DDRM.mult(F, x, xNext);
        this.x = xNext;

        DMatrixRMaj FP = new  DMatrixRMaj(4, 4);
        CommonOps_DDRM.mult(F, P, FP);

        DMatrixRMaj F_transpose = new DMatrixRMaj(4, 4);
        CommonOps_DDRM.transpose(F, F_transpose);

        DMatrixRMaj FPF_transpose = new DMatrixRMaj(4, 4);
        CommonOps_DDRM.mult(FP, F_transpose, FPF_transpose);


        CommonOps_DDRM.add(FPF_transpose, Q, P);
    }

    public void update(double zX, double zY) {

        DMatrixRMaj z = new DMatrixRMaj(new double [][]{{zX},{zY}});

        DMatrixRMaj H_transpose =  new DMatrixRMaj(4, 2);
        CommonOps_DDRM.transpose(H, H_transpose);

        DMatrixRMaj HP = new  DMatrixRMaj(2, 4);
        CommonOps_DDRM.mult(H, P, HP);

        DMatrixRMaj HPH_transpose = new DMatrixRMaj(2, 2);
        CommonOps_DDRM.mult(HP, H_transpose, HPH_transpose);

        DMatrixRMaj S = new DMatrixRMaj(2, 2);
        CommonOps_DDRM.add(HPH_transpose, R, S);

        DMatrixRMaj S_inverted = new DMatrixRMaj(2, 2);
        CommonOps_DDRM.invert(S, S_inverted);

        DMatrixRMaj PH_transpose = new DMatrixRMaj(4, 2);
        CommonOps_DDRM.mult(P, H_transpose, PH_transpose);

        DMatrixRMaj K =  new DMatrixRMaj(4, 2);
        CommonOps_DDRM.mult(PH_transpose, S_inverted, K);

        DMatrixRMaj Hx = new  DMatrixRMaj(2, 1);
        CommonOps_DDRM.mult(H, x, Hx);

        DMatrixRMaj y = new DMatrixRMaj(2, 1);
        CommonOps_DDRM.subtract(z, Hx, y);

        DMatrixRMaj Ky = new  DMatrixRMaj(4, 1);
        CommonOps_DDRM.mult(K, y, Ky);
        CommonOps_DDRM.add(x, Ky, x);

        DMatrixRMaj KH = new  DMatrixRMaj(4, 4);
        CommonOps_DDRM.mult(K, H, KH);

        DMatrixRMaj I = new DMatrixRMaj(4, 4);
        CommonOps_DDRM.setIdentity(I);

        DMatrixRMaj I_minus_KH = new DMatrixRMaj(4, 4);
        CommonOps_DDRM.subtract(I, KH, I_minus_KH);

        DMatrixRMaj PNext = new DMatrixRMaj(4, 4);
        CommonOps_DDRM.mult(I_minus_KH, P,  PNext);
        this.P = PNext;
    }

        public double getFilteredX(){
        return x.get(0, 0);
        }

        public double getFilteredY(){
            return x.get(1, 0);
    }
        public double getVelocityX(){
            return x.get(2, 0);
    }

        public double getVelocityY(){
            return x.get(3, 0);
    }

}
