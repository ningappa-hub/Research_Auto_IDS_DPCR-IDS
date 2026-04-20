// --------------------------------------------------------------------------
// DecisionAggregator.cc — Time-bucket gateway-level alert merging.
// Exact port of dpcr_ids.runtime.aggregator.DecisionAggregator
// --------------------------------------------------------------------------
#include "DecisionAggregator.h"
#include "../msg/AlertMsg_m.h"

namespace dpcrids {

Define_Module(DecisionAggregator);

int DecisionAggregator::decisionPriority(const std::string& decision)
{
    if (decision == "NORMAL")   return 0;
    if (decision == "ATTACK")   return 1;
    if (decision == "ESCALATE") return 2;
    return -1;
}

void DecisionAggregator::initialize()
{
    bucketMs_ = par("bucketMs").doubleValue();
    failOpen_ = par("failOpen").boolValue();

    aggDecisionSignal_ = registerSignal("aggregatedDecision");
    bucketSizeSignal_  = registerSignal("bucketSize");
    e2eLatencySignal_  = registerSignal("endToEndLatencyMs");

    // Schedule periodic flush timer (every bucketMs)
    flushTimer_ = new cMessage("flushTimer");
    scheduleAt(simTime() + SimTime(bucketMs_, SIMTIME_MS), flushTimer_);

    EV_INFO << "DecisionAggregator initialized | bucketMs=" << bucketMs_
            << " | failOpen=" << failOpen_ << endl;
}

int64_t DecisionAggregator::computeBucketId(simtime_t ts)
{
    double tsMs = ts.dbl() * 1000.0;
    return static_cast<int64_t>(tsMs / bucketMs_);
}

void DecisionAggregator::handleMessage(cMessage *msg)
{
    if (msg->isSelfMessage()) {
        // Flush timer fired
        flushBuckets(simTime());
        scheduleAt(simTime() + SimTime(bucketMs_, SIMTIME_MS), flushTimer_);
        return;
    }

    AlertMsg *alertMsg = check_and_cast<AlertMsg *>(msg);

    AlertEntry entry;
    entry.decision         = alertMsg->getDecision();
    entry.path             = alertMsg->getPath();
    entry.pAttackRaw       = alertMsg->getPAttackRaw();
    entry.pAttackCalibrated= alertMsg->getPAttackCalibrated();
    entry.latencyMs        = alertMsg->getLatencyMs();
    entry.escalateFlag     = alertMsg->getEscalateFlag();
    entry.timestamp        = alertMsg->getTimestamp();

    int64_t bucketId = computeBucketId(entry.timestamp);
    buckets_[bucketId].push_back(entry);
    totalAlerts_++;

    delete msg;
}

AlertEntry DecisionAggregator::mergeAlerts(const std::vector<AlertEntry>& alerts)
{
    // Select highest priority decision (NORMAL < ATTACK < ESCALATE)
    // Break ties by highest calibrated probability
    const AlertEntry* best = &alerts[0];
    for (size_t i = 1; i < alerts.size(); i++) {
        int priCurrent = decisionPriority(best->decision);
        int priCandidate = decisionPriority(alerts[i].decision);
        if (priCandidate > priCurrent ||
            (priCandidate == priCurrent &&
             alerts[i].pAttackCalibrated > best->pAttackCalibrated)) {
            best = &alerts[i];
        }
    }

    AlertEntry merged = *best;
    // Set escalate if any alert escalated
    for (const auto& a : alerts) {
        if (a.escalateFlag) {
            merged.escalateFlag = true;
            break;
        }
    }
    return merged;
}

void DecisionAggregator::flushBuckets(simtime_t upTo)
{
    int64_t limitId = computeBucketId(upTo);

    auto it = buckets_.begin();
    while (it != buckets_.end()) {
        if (it->first <= limitId && !it->second.empty()) {
            AlertEntry merged = mergeAlerts(it->second);

            // Emit statistics
            emit(aggDecisionSignal_,
                 static_cast<long>(decisionPriority(merged.decision)));
            emit(bucketSizeSignal_, static_cast<long>(it->second.size()));

            // Compute end-to-end latency: simulation time elapsed since the
            // alert timestamp until now
            double e2eMs = (simTime() - merged.timestamp).dbl() * 1000.0
                           + merged.latencyMs;
            emit(e2eLatencySignal_, e2eMs);

            // Build and send gateway-level alert
            AlertMsg *gwAlert = new AlertMsg("gatewayAlert");
            gwAlert->setDecision(merged.decision.c_str());
            gwAlert->setPath("gateway");
            gwAlert->setPAttackRaw(merged.pAttackRaw);
            gwAlert->setPAttackCalibrated(merged.pAttackCalibrated);
            gwAlert->setLatencyMs(e2eMs);
            gwAlert->setEscalateFlag(merged.escalateFlag);
            gwAlert->setTimestamp(merged.timestamp);

            send(gwAlert, "gatewayOut");
            totalFlushed_++;

            it = buckets_.erase(it);
        } else {
            ++it;
        }
    }
}

void DecisionAggregator::finish()
{
    cancelAndDelete(flushTimer_);
    flushTimer_ = nullptr;

    // Flush remaining
    if (!buckets_.empty()) {
        for (auto& kv : buckets_) {
            if (!kv.second.empty()) {
                totalFlushed_++;
            }
        }
    }

    recordScalar("totalAlerts", totalAlerts_);
    recordScalar("totalFlushed", totalFlushed_);

    EV_INFO << "DecisionAggregator finished | totalAlerts=" << totalAlerts_
            << " | totalFlushed=" << totalFlushed_ << endl;
}

} // namespace dpcrids
