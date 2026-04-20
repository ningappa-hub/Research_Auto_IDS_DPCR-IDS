// --------------------------------------------------------------------------
// EthExpertIDS.h — Ethernet CNN expert: payload images → ONNX inference.
// --------------------------------------------------------------------------
#ifndef DPCR_IDS_ETH_EXPERT_IDS_H
#define DPCR_IDS_ETH_EXPERT_IDS_H

#include <omnetpp.h>
#include <vector>
#include <memory>
#include "../utils/OnnxInference.h"
#include "../utils/TemperatureScaler.h"

using namespace omnetpp;

namespace dpcrids {

/**
 * Ethernet Expert IDS Module.
 *
 * Receives Ethernet frames, constructs [3, 32, 32] image tensors from
 * payload bytes, runs CNN student ONNX model, and outputs [1, 129].
 */
class EthExpertIDS : public cSimpleModule {
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

private:
    std::unique_ptr<OnnxInference> onnxModel_;
    TemperatureScaler scaler_;

    int payloadBytes_;
    int frameHeight_;
    int frameWidth_;
    int inChannels_;

    // Statistics signals
    simsignal_t logitSignal_;
    simsignal_t calProbSignal_;
    simsignal_t inferenceMsSignal_;

    long framesProcessed_ = 0;

    /**
     * Convert raw payload bytes into [3, 32, 32] image tensor.
     * First 1024 bytes are reshaped; zero-padded if shorter.
     */
    std::vector<float> payloadToImage(const std::vector<uint8_t>& payload);
};

} // namespace dpcrids

#endif // DPCR_IDS_ETH_EXPERT_IDS_H
