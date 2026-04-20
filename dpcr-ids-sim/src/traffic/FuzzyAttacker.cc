// --------------------------------------------------------------------------
// FuzzyAttacker.cc — Random CAN ID/payload fuzzing attack.
// --------------------------------------------------------------------------
#include <omnetpp.h>
#include "../msg/CanFrameMsg_m.h"

using namespace omnetpp;

namespace dpcrids {

class FuzzyAttacker : public cSimpleModule {
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
    bool attacking_ = false;
    long attackFramesSent_ = 0;
};

Define_Module(FuzzyAttacker);

void FuzzyAttacker::initialize()
{
    attackInterval_  = par("attackInterval").doubleValue();
    attackStartTime_ = par("attackStartTime").doubleValue();
    attackDuration_  = par("attackDuration").doubleValue();

    attackTimer_ = new cMessage("fuzzyAttackTimer");
    scheduleAt(simTime() + attackStartTime_, attackTimer_);
}

void FuzzyAttacker::handleMessage(cMessage *msg)
{
    if (msg == stopTimer_) {
        attacking_ = false;
        cancelAndDelete(stopTimer_);
        stopTimer_ = nullptr;
        cancelAndDelete(attackTimer_);
        attackTimer_ = nullptr;
        EV_INFO << "Fuzzy attack stopped after " << attackFramesSent_
                << " frames." << endl;
        return;
    }

    if (msg == attackTimer_) {
        if (!attacking_) {
            attacking_ = true;
            stopTimer_ = new cMessage("fuzzyStopTimer");
            scheduleAt(simTime() + attackDuration_, stopTimer_);
            EV_INFO << "Fuzzy attack STARTED at t=" << simTime() << endl;
        }

        if (attacking_) {
            // Random CAN ID (standard: 0x000 to 0x7FF)
            CanFrameMsg *frame = new CanFrameMsg("fuzzyFrame");
            frame->setCanId(intuniform(0x000, 0x7FF));
            frame->setDlc(intuniform(1, 8));

            // Random payload bytes
            for (int i = 0; i < 8; i++) {
                frame->setData(i, static_cast<uint8_t>(intuniform(0, 255)));
            }

            frame->setLabel(1);
            frame->setAttackType("fuzzy");

            send(frame, "canOut");
            attackFramesSent_++;

            scheduleAt(simTime() + attackInterval_, attackTimer_);
        }
    }
}

void FuzzyAttacker::finish()
{
    if (attackTimer_) { cancelAndDelete(attackTimer_); attackTimer_ = nullptr; }
    if (stopTimer_)   { cancelAndDelete(stopTimer_); stopTimer_ = nullptr; }
    recordScalar("fuzzyFramesSent", attackFramesSent_);
}

} // namespace dpcrids
