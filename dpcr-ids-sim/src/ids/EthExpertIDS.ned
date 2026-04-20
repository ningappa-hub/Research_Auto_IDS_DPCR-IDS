// --------------------------------------------------------------------------
// EthExpertIDS.ned — Automotive Ethernet intrusion detection expert module.
// --------------------------------------------------------------------------

package dpcrids.ids;

simple EthExpertIDS
{
    parameters:
        string onnxModelPath = default("models/eth_student.onnx");
        double temperature = default(0.5);    // from calibration/ethernet.json
        int payloadBytes = default(1024);
        int frameHeight = default(32);
        int frameWidth = default(32);
        int inChannels = default(3);
        int embeddingDim = default(128);
        @display("i=block/cogwheel,blue");
        @signal[ethLogit](type=double);
        @signal[ethCalProb](type=double);
        @signal[ethInferenceMs](type=double);
        @statistic[ethLogit](record=vector,mean,max);
        @statistic[ethCalProb](record=vector,histogram);
        @statistic[ethInferenceMs](record=vector,mean,max,timeavg);

    gates:
        input ethFrameIn;       // raw Ethernet frames from gateway
        output expertOut;       // [1, 129] logit+embedding to fusion
}
