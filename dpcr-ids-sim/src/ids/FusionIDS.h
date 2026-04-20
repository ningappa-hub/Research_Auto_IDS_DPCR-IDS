// --------------------------------------------------------------------------
// FusionIDS.h — Late fusion head combining CAN + Ethernet expert outputs.
// --------------------------------------------------------------------------
#ifndef DPCR_IDS_FUSION_IDS_H
#define DPCR_IDS_FUSION_IDS_H

#include <omnetpp.h>
#include <vector>
#include <memory>
#include "../utils/OnnxInference.h"
#include "../utils/TemperatureScaler.h"

using namespace omnetpp;

namespace dpcrids {

/**
 * Late Fusion IDS Module.
 *
 * Pairs CAN and Ethernet expert outputs by time bucket, stacks them to
 * [1, 2, 129], runs the fusion student ONNX model, and emits a fused
 * probability to the ConfidenceRouter.
 */
class FusionIDS : public cSimpleModule {
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

private:
    std::unique_ptr<OnnxInference> onnxModel_;
    TemperatureScaler scaler_;

    int numExperts_;
    int expertDim_;
    double bucketMs_;

    // Buffered expert outputs waiting for pairing
    struct ExpertData {
        float logit;
        float rawProb;
        float calProb;
        std::vector<float> embedding; // 128-dim
        simtime_t timestamp;
        bool valid = false;
    };

    ExpertData pendingCan_;
    ExpertData pendingEth_;

    // Statistics
    simsignal_t fusionLogitSignal_;
    simsignal_t fusionCalProbSignal_;
    simsignal_t fusionInferenceMsSignal_;

    long fusionsPaired_ = 0;

    void tryFusion();
    bool withinBucket(simtime_t t1, simtime_t t2);
};

} // namespace dpcrids

#endif // DPCR_IDS_FUSION_IDS_H
