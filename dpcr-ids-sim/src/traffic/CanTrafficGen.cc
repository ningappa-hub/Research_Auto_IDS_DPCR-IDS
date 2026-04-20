// --------------------------------------------------------------------------
// CanTrafficGen.cc — Generates periodic normal CAN frames.
// --------------------------------------------------------------------------
#include <omnetpp.h>
#include "../msg/CanFrameMsg_m.h"
#include <cstdlib>

using namespace omnetpp;

namespace dpcrids {

class CanTrafficGen : public cSimpleModule {
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;

private:
    cMessage *sendTimer_ = nullptr;
    double sendInterval_;
    int numCanIds_;
    int startCanId_;
    int currentIdIndex_ = 0;
    uint8_t lastPayloads_[2048][8] = {};  // track last payload per ID
    long framesSent_ = 0;
};

Define_Module(CanTrafficGen);

void CanTrafficGen::initialize()
{
    sendInterval_ = par("sendInterval").doubleValue();
    numCanIds_    = par("numCanIds").intValue();
    startCanId_   = par("startCanId").intValue();

    sendTimer_ = new cMessage("canSendTimer");
    scheduleAt(simTime() + sendInterval_, sendTimer_);
}

void CanTrafficGen::handleMessage(cMessage *msg)
{
    if (!msg->isSelfMessage()) {
        delete msg;
        return;
    }

    // Generate a normal CAN frame
    uint32_t canId = startCanId_ + (currentIdIndex_ % numCanIds_);

    CanFrameMsg *frame = new CanFrameMsg("canFrame");
    frame->setCanId(canId);
    frame->setDlc(8);

    // Generate realistic payload: small increments from last value (sensor-like)
    for (int i = 0; i < 8; i++) {
        int delta = intuniform(-3, 3);
        int newVal = static_cast<int>(lastPayloads_[currentIdIndex_ % numCanIds_][i])
                     + delta;
        newVal = std::max(0, std::min(255, newVal));
        frame->setData(i, static_cast<uint8_t>(newVal));
        lastPayloads_[currentIdIndex_ % numCanIds_][i] =
            static_cast<uint8_t>(newVal);
    }

    frame->setLabel(0);  // normal traffic
    frame->setAttackType("normal");

    send(frame, "canOut");
    framesSent_++;
    currentIdIndex_++;

    // Reschedule with slight jitter for realism
    double jitter = uniform(-sendInterval_ * 0.1, sendInterval_ * 0.1);
    scheduleAt(simTime() + sendInterval_ + jitter, sendTimer_);
}

} // namespace dpcrids
