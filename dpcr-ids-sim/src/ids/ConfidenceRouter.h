// --------------------------------------------------------------------------
// ConfidenceRouter.h — Fast/heavy path routing by calibrated confidence.
// --------------------------------------------------------------------------
#ifndef DPCR_IDS_CONFIDENCE_ROUTER_H
#define DPCR_IDS_CONFIDENCE_ROUTER_H

#include <omnetpp.h>

using namespace omnetpp;

namespace dpcrids {

class ConfidenceRouter : public cSimpleModule {
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

private:
    double tauLow_;
    double tauHigh_;
    double fallbackLow_;
    double fallbackHigh_;
    bool expertOverride_;

    simsignal_t decisionSignal_;
    simsignal_t pathSignal_;
    simsignal_t latencySignal_;

    long normalCount_ = 0;
    long attackCount_ = 0;
    long escalateCount_ = 0;
    long fastCount_ = 0;
    long heavyCount_ = 0;
    long expertOverrideCount_ = 0;
};

} // namespace dpcrids

#endif // DPCR_IDS_CONFIDENCE_ROUTER_H
