// --------------------------------------------------------------------------
// EthTrafficGen.cc — Generates normal Automotive Ethernet frames.
// --------------------------------------------------------------------------
#include <omnetpp.h>
#include "../msg/EthFrameMsg_m.h"
#include <sstream>

using namespace omnetpp;

namespace dpcrids {

class EthTrafficGen : public cSimpleModule {
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;

private:
    cMessage *sendTimer_ = nullptr;
    double sendInterval_;
    int payloadLength_;
    long framesSent_ = 0;

    // Track previous payload bytes for correlated (realistic) payload evolution.
    // Real SOME/IP / DoIP frames carry slow-changing sensor values — NOT random noise.
    // Using correlated payloads keeps the delta-channel near zero for normal traffic,
    // matching the distribution seen during training on the AutoEth dataset.
    std::vector<uint8_t> lastPayload_;
};

Define_Module(EthTrafficGen);

void EthTrafficGen::initialize()
{
    sendInterval_  = par("sendInterval").doubleValue();
    payloadLength_ = par("payloadLength").intValue();

    // Initialise with mid-range sensor values so the first delta is near zero
    lastPayload_.assign(payloadLength_, 128);

    sendTimer_ = new cMessage("ethSendTimer");
    scheduleAt(simTime() + sendInterval_, sendTimer_);

    getDisplayString().setTagArg("t", 0, "ETH ECU idle");
    getDisplayString().setTagArg("i", 1, "gray");
}

void EthTrafficGen::handleMessage(cMessage *msg)
{
    if (!msg->isSelfMessage()) {
        delete msg;
        return;
    }

    EthFrameMsg *frame = new EthFrameMsg("ethFrame");

    int len = par("payloadLength").intValue();
    frame->setPayloadArraySize(len);
    frame->setPayloadLength(len);

    // --- Realistic automotive Ethernet payload ---
    // Header region (bytes 0-15): structured SOME/IP-style fields that
    // change slowly with each frame (service-ID, method-ID, counter, etc.)
    for (int i = 0; i < std::min(len, 16); i++) {
        uint8_t next = static_cast<uint8_t>((lastPayload_[i] + intuniform(0, 2)) % 256);
        frame->setPayload(i, next);
        lastPayload_[i] = next;
    }

    // Payload region (bytes 16+): sensor / actuator values that evolve
    // smoothly (small increments), matching real SOME/IP sensor streams.
    for (int i = 16; i < len; i++) {
        int delta = intuniform(-4, 4);   // small signed step, like a sensor reading
        int next  = static_cast<int>(lastPayload_[i]) + delta;
        next = std::max(0, std::min(255, next));
        frame->setPayload(i, static_cast<uint8_t>(next));
        lastPayload_[i] = static_cast<uint8_t>(next);
    }

    frame->setLabel(0);
    frame->setAttackType("normal");
    frame->setProtocol("SOME/IP");

    send(frame, "ethOut");
    framesSent_++;

    if (framesSent_ % 100 == 0) {
        std::ostringstream status;
        status << "ETH ECU tx=" << framesSent_;
        getDisplayString().setTagArg("t", 0, status.str().c_str());
        getDisplayString().setTagArg("i", 1, "blue");
    }

    double jitter = uniform(-sendInterval_ * 0.05, sendInterval_ * 0.05);
    scheduleAt(simTime() + sendInterval_ + jitter, sendTimer_);
}

} // namespace dpcrids
