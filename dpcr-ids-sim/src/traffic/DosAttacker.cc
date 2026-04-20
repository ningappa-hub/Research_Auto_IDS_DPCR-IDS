// --------------------------------------------------------------------------
// DosAttacker.cc — DoS flood attack: high-frequency CAN frame injection.
// --------------------------------------------------------------------------
#include <omnetpp.h>
#include "../msg/CanFrameMsg_m.h"

using namespace omnetpp;

namespace dpcrids {

class DosAttacker : public cSimpleModule {
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
    int targetCanId_;
    bool attacking_ = false;
    long attackFramesSent_ = 0;
};

Define_Module(DosAttacker);

void DosAttacker::initialize()
{
    attackInterval_  = par("attackInterval").doubleValue();
    attackStartTime_ = par("attackStartTime").doubleValue();
    attackDuration_  = par("attackDuration").doubleValue();
    targetCanId_     = par("targetCanId").intValue();

    // Schedule attack start
    attackTimer_ = new cMessage("dosAttackTimer");
    scheduleAt(simTime() + attackStartTime_, attackTimer_);

    EV_INFO << "DosAttacker scheduled: start=" << attackStartTime_
            << "s duration=" << attackDuration_
            << "s interval=" << attackInterval_ << "s" << endl;
}

void DosAttacker::handleMessage(cMessage *msg)
{
    if (msg == stopTimer_) {
        attacking_ = false;
        EV_INFO << "DoS attack stopped after " << attackFramesSent_
                << " frames." << endl;
        cancelAndDelete(stopTimer_);
        stopTimer_ = nullptr;
        cancelAndDelete(attackTimer_);
        attackTimer_ = nullptr;
        return;
    }

    if (msg == attackTimer_) {
        if (!attacking_) {
            // Start the attack
            attacking_ = true;
            stopTimer_ = new cMessage("dosStopTimer");
            scheduleAt(simTime() + attackDuration_, stopTimer_);
            EV_INFO << "DoS attack STARTED at t=" << simTime() << endl;
        }

        if (attacking_) {
            // Inject DoS frame: highest priority ID (0x000), all zeros or all 0xFF
            CanFrameMsg *frame = new CanFrameMsg("dosFrame");
            frame->setCanId(targetCanId_);
            frame->setDlc(8);
            for (int i = 0; i < 8; i++) {
                frame->setData(i, 0x00);
            }
            frame->setLabel(1);  // attack
            frame->setAttackType("dos");

            send(frame, "canOut");
            attackFramesSent_++;

            // Schedule next flood frame
            scheduleAt(simTime() + attackInterval_, attackTimer_);
        }
    }
}

void DosAttacker::finish()
{
    if (attackTimer_) {
        cancelAndDelete(attackTimer_);
        attackTimer_ = nullptr;
    }
    if (stopTimer_) {
        cancelAndDelete(stopTimer_);
        stopTimer_ = nullptr;
    }
    recordScalar("dosFramesSent", attackFramesSent_);
}

} // namespace dpcrids
