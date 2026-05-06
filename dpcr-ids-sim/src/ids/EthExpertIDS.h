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

    // Previous payload tracking for delta channel computation
    // Mirrors Python: prev_by_protocol
    std::vector<uint8_t> prevPayload_;
    bool hasPrevPayload_ = false;
    double prevTsMs_ = 0.0;

    /**
     * Convert raw payload bytes into [4, 32, 32] image tensor.
     * Four channels matching Python bytes_to_byte_image():
     *   Channel 0: value     — byte / 255.0
     *   Channel 1: delta     — (current - previous) / 255.0, clamped to [-1, 1]
     *   Channel 2: position  — byte_offset / payload_bytes
     *   Channel 3: temporal  — min(max(iat_ms / 100.0, 0.0), 1.0)
     */
    std::vector<float> payloadToImage(const std::vector<uint8_t>& payload,
                                       const std::vector<uint8_t>& prevPayload,
                                       double iatMs);
};

} // namespace dpcrids

#endif // DPCR_IDS_ETH_EXPERT_IDS_H
