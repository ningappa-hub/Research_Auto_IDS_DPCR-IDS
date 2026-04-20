// --------------------------------------------------------------------------
// DecisionAggregator.h — Time-bucket aggregation of IDS alerts.
// --------------------------------------------------------------------------
#ifndef DPCR_IDS_DECISION_AGGREGATOR_H
#define DPCR_IDS_DECISION_AGGREGATOR_H

#include <omnetpp.h>
#include <map>
#include <vector>
#include <string>

using namespace omnetpp;

namespace dpcrids {

struct AlertEntry {
    std::string decision;   // "NORMAL", "ATTACK", "ESCALATE"
    std::string path;
    double pAttackRaw;
    double pAttackCalibrated;
    double latencyMs;
    bool escalateFlag;
    simtime_t timestamp;
};

class DecisionAggregator : public cSimpleModule {
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

private:
    double bucketMs_;
    bool failOpen_;

    // Buckets keyed by bucket ID
    std::map<int64_t, std::vector<AlertEntry>> buckets_;

    // Timer for periodic flushing
    cMessage *flushTimer_ = nullptr;

    simsignal_t aggDecisionSignal_;
    simsignal_t bucketSizeSignal_;
    simsignal_t e2eLatencySignal_;

    long totalAlerts_ = 0;
    long totalFlushed_ = 0;

    int64_t computeBucketId(simtime_t ts);
    void flushBuckets(simtime_t upTo);
    AlertEntry mergeAlerts(const std::vector<AlertEntry>& alerts);
    static int decisionPriority(const std::string& decision);
};

} // namespace dpcrids

#endif // DPCR_IDS_DECISION_AGGREGATOR_H
