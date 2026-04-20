// --------------------------------------------------------------------------
// CanExpertIDS.ned — CAN bus intrusion detection expert module.
// Intercepts CAN frames, extracts features, runs TCN inference via ONNX.
// --------------------------------------------------------------------------

package dpcrids.ids;

simple CanExpertIDS
{
    parameters:
        string onnxModelPath = default("models/can_student.onnx");
        double temperature = default(0.95);   // from calibration/can.json
        int windowSize = default(100);
        int stride = default(50);
        int numFeatures = default(16);
        int embeddingDim = default(128);
        @display("i=block/cogwheel,red");
        @signal[canLogit](type=double);
        @signal[canCalProb](type=double);
        @signal[canInferenceMs](type=double);
        @statistic[canLogit](record=vector,mean,max);
        @statistic[canCalProb](record=vector,histogram);
        @statistic[canInferenceMs](record=vector,mean,max,timeavg);

    gates:
        input canFrameIn;       // raw CAN frames from gateway
        output expertOut;       // [1, 129] logit+embedding to fusion
}
