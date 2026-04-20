// --------------------------------------------------------------------------
// FusionIDS.ned — Late fusion meta-model combining CAN and Ethernet experts.
// --------------------------------------------------------------------------

package dpcrids.ids;

simple FusionIDS
{
    parameters:
        string onnxModelPath = default("models/fusion_student.onnx");
        double temperature = default(1.1);    // from calibration/fusion.json
        int numExperts = default(2);
        int expertDim = default(129);         // 1 logit + 128 embedding
        double bucketMs = default(250);       // time bucket for pairing
        @display("i=block/join,green");
        @signal[fusionLogit](type=double);
        @signal[fusionCalProb](type=double);
        @signal[fusionInferenceMs](type=double);
        @statistic[fusionLogit](record=vector,mean,max);
        @statistic[fusionCalProb](record=vector,histogram);
        @statistic[fusionInferenceMs](record=vector,mean,max,timeavg);

    gates:
        input canExpertIn;     // [1, 129] from CAN expert
        input ethExpertIn;     // [1, 129] from Ethernet expert
        output fusionOut;      // fused decision to ConfidenceRouter
}
