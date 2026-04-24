// --------------------------------------------------------------------------
// CanExpertIDS.h — CAN TCN expert: window CAN frames → ONNX inference.
// --------------------------------------------------------------------------
#ifndef DPCR_IDS_CAN_EXPERT_IDS_H
#define DPCR_IDS_CAN_EXPERT_IDS_H

#include <omnetpp.h>
#include <vector>
#include <memory>
#include "../utils/OnnxInference.h"
#include "../utils/FeatureExtractor.h"
#include "../utils/TemperatureScaler.h"

using namespace omnetpp;

namespace dpcrids {

/**
 * CAN Expert IDS Module.
 *
 * Buffers incoming CAN frames into sliding windows of [windowSize] frames
 * with [stride] step. For each complete window:
 *   1. Extracts [16, windowSize] feature tensor
 *   2. Runs CAN student ONNX model → logit (scalar)
 *   3. Runs forward_features → embedding (128-dim)
 *   4. Applies temperature calibration
 *   5. Sends [1, 129] (logit + embedding) to FusionIDS
 */
class CanExpertIDS : public cSimpleModule {
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

private:
    // ONNX inference engines (main model outputs logit; we use same model's
    // intermediate layer for embedding)
    std::unique_ptr<OnnxInference> onnxModel_;
    TemperatureScaler scaler_;
    ZScoreParams zscore_;

    // Windowing
    std::vector<CanFrame> frameBuffer_;
    int windowSize_;
    int stride_;

    // Statistics signals
    simsignal_t logitSignal_;
    simsignal_t calProbSignal_;
    simsignal_t inferenceMsSignal_;

    // Counters
    long windowsProcessed_ = 0;
    long framesReceived_ = 0;

    void processWindow(const std::vector<CanFrame>& window);
};

} // namespace dpcrids

#endif // DPCR_IDS_CAN_EXPERT_IDS_H
