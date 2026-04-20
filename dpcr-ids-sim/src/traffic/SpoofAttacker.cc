// --------------------------------------------------------------------------
// SpoofAttacker.cc — Masquerade attack: impersonates specific ECU.
// --------------------------------------------------------------------------
#include <omnetpp.h>
#include "../msg/CanFrameMsg_m.h"

using namespace omnetpp;

namespace dpcrids {

class SpoofAttacker : public cSimpleModule {
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

private:
    cMessage *attackTimer_ = nullptr;
    cMessage *stopTimer_ = nullptr;
    double attackInterval_;
    double attackStartTime_;
    double attackDuration_;
    int spoofCanId_;
    std::string spoofType_;
    bool attacking_ = false;
    long attackFramesSent_ = 0;
};

Define_Module(SpoofAttacker);

void SpoofAttacker::initialize()
{
    attackInterval_  = par("attackInterval").doubleValue();
    attackStartTime_ = par("attackStartTime").doubleValue();
    attackDuration_  = par("attackDuration").doubleValue();
    spoofCanId_      = par("spoofCanId").intValue();
    spoofType_       = par("spoofType").stdstringValue();

    attackTimer_ = new cMessage("spoofAttackTimer");
    scheduleAt(simTime() + attackStartTime_, attackTimer_);
}

void SpoofAttacker::handleMessage(cMessage *msg)
{
    if (msg == stopTimer_) {
        attacking_ = false;
        cancelAndDelete(stopTimer_);
        stopTimer_ = nullptr;
        cancelAndDelete(attackTimer_);
        attackTimer_ = nullptr;
        return;
    }

    if (msg == attackTimer_) {
        if (!attacking_) {
            attacking_ = true;
            stopTimer_ = new cMessage("spoofStopTimer");
            scheduleAt(simTime() + attackDuration_, stopTimer_);
            EV_INFO << "Spoof (" << spoofType_ << ") attack STARTED at t="
                    << simTime() << " | targeting CAN ID 0x"
                    << std::hex << spoofCanId_ << std::dec << endl;
        }

        if (attacking_) {
            CanFrameMsg *frame = new CanFrameMsg("spoofFrame");
            frame->setCanId(spoofCanId_);
            frame->setDlc(8);

            if (spoofType_ == "gear") {
                // Gear spoofing: inject sudden gear state changes
                // Byte 0-1: gear position (abrupt), rest: plausible sensor data
                frame->setData(0, static_cast<uint8_t>(intuniform(0, 6)));
                frame->setData(1, 0xFF);
                for (int i = 2; i < 8; i++) {
                    frame->setData(i, static_cast<uint8_t>(intuniform(100, 200)));
                }
            } else {
                // RPM spoofing: inject extreme RPM values
                // Bytes 0-1: RPM high (big-endian), rest: engine data
                uint16_t fakeRpm = static_cast<uint16_t>(intuniform(7000, 9000));
                frame->setData(0, static_cast<uint8_t>((fakeRpm >> 8) & 0xFF));
                frame->setData(1, static_cast<uint8_t>(fakeRpm & 0xFF));
                for (int i = 2; i < 8; i++) {
                    frame->setData(i, static_cast<uint8_t>(intuniform(50, 250)));
                }
            }

            frame->setLabel(1);
            frame->setAttackType(spoofType_.c_str());

            send(frame, "canOut");
            attackFramesSent_++;

            scheduleAt(simTime() + attackInterval_, attackTimer_);
        }
    }
}

void SpoofAttacker::finish()
{
    if (attackTimer_) { cancelAndDelete(attackTimer_); attackTimer_ = nullptr; }
    if (stopTimer_)   { cancelAndDelete(stopTimer_); stopTimer_ = nullptr; }
    recordScalar("spoofFramesSent", attackFramesSent_);
}

} // namespace dpcrids
