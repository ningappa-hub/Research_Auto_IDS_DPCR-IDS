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
};

Define_Module(EthTrafficGen);

void EthTrafficGen::initialize()
{
    sendInterval_  = par("sendInterval").doubleValue();
    payloadLength_ = par("payloadLength").intValue();

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

    // Generate structured payload mimicking SOME/IP or DoIP headers
    for (int i = 0; i < len; i++) {
        if (i < 16) {
            // Header region: structured bytes
            frame->setPayload(i, static_cast<uint8_t>((i * 17 + framesSent_) % 256));
        } else {
            // Payload region: sensor-like data
            frame->setPayload(i, static_cast<uint8_t>(intuniform(0, 255)));
        }
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
