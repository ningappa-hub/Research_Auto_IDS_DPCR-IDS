// --------------------------------------------------------------------------
// ConfidenceRouter.cc — Routes fused probabilities through fast/heavy paths.
// Exact port of dpcr_ids.runtime.router.ConfidenceRouter
// --------------------------------------------------------------------------
#include "ConfidenceRouter.h"
#include "../msg/FusionResult_m.h"
#include "../msg/AlertMsg_m.h"
#include <chrono>

namespace dpcrids {

Define_Module(ConfidenceRouter);

void ConfidenceRouter::initialize()
{
    tauLow_      = par("tauLow").doubleValue();
    tauHigh_     = par("tauHigh").doubleValue();
    fallbackLow_ = par("fallbackUncertaintyLow").doubleValue();
    fallbackHigh_= par("fallbackUncertaintyHigh").doubleValue();
    expertOverride_ = par("expertOverride").boolValue();

    decisionSignal_ = registerSignal("routeDecision");
    pathSignal_     = registerSignal("routePath");
    latencySignal_  = registerSignal("routingLatencyMs");

    ASSERT(0.0 <= tauLow_ && tauLow_ <= tauHigh_ && tauHigh_ <= 1.0);

    EV_INFO << "ConfidenceRouter initialized | tauLow=" << tauLow_
            << " | tauHigh=" << tauHigh_
            << " | expertOverride=" << (expertOverride_ ? "true" : "false")
            << endl;
}

void ConfidenceRouter::handleMessage(cMessage *msg)
{
    auto startTime = std::chrono::high_resolution_clock::now();

    FusionResult *fusion = check_and_cast<FusionResult *>(msg);

    double calProb = fusion->getCalibratedProb();
    double rawProb = fusion->getRawProb();

    int decision;    // 0=NORMAL, 1=ATTACK, 2=ESCALATE
    int pathType;    // 0=fast, 1=heavy
    std::string decisionStr;
    std::string pathStr;

    // Expert-aware override: if BOTH individual experts independently
    // predict NORMAL with high confidence, short-circuit to NORMAL
    // regardless of the fusion output.  This prevents false positives
    // when the fusion model has insufficient joint-normal training data.
    if (expertOverride_) {
        double canProb = fusion->getCanRawProb();
        double ethProb = fusion->getEthRawProb();
        if (canProb <= tauLow_ && ethProb <= tauLow_) {
            decision = 0;
            decisionStr = "NORMAL";
            pathType = 0;
            pathStr = "fast";
            normalCount_++;
            fastCount_++;
            expertOverrideCount_++;

            EV_DEBUG << "Expert override: both experts NORMAL (CAN="
                     << canProb << " ETH=" << ethProb
                     << ") → overriding fusion calProb=" << calProb << endl;

            // Skip to alert emission
            goto emitAlert;
        }
    }

    if (calProb >= tauHigh_) {
        // High confidence attack → fast path
        decision = 1;
        decisionStr = "ATTACK";
        pathType = 0;
        pathStr = "fast";
        attackCount_++;
        fastCount_++;
    } else if (calProb <= tauLow_) {
        // High confidence normal → fast path
        decision = 0;
        decisionStr = "NORMAL";
        pathType = 0;
        pathStr = "fast";
        normalCount_++;
        fastCount_++;
    } else {
        // Uncertain → heavy path (fallback / escalate)
        pathType = 1;
        pathStr = "heavy";
        heavyCount_++;

        // Apply fallback uncertainty decision (mirrors Python logic)
        if (calProb > fallbackLow_ && calProb < fallbackHigh_) {
            decision = 2; // ESCALATE
            decisionStr = "ESCALATE";
            escalateCount_++;
        } else if (calProb >= fallbackHigh_) {
            decision = 1; // ATTACK
            decisionStr = "ATTACK";
            attackCount_++;
        } else {
            decision = 0; // NORMAL
            decisionStr = "NORMAL";
            normalCount_++;
        }
    }

emitAlert:
    auto endTime = std::chrono::high_resolution_clock::now();
    double latencyMs = std::chrono::duration<double, std::milli>(
        endTime - startTime).count();

    // Emit statistics
    emit(decisionSignal_, static_cast<long>(decision));
    emit(pathSignal_, static_cast<long>(pathType));
    emit(latencySignal_, latencyMs);

    // Build alert message
    AlertMsg *alert = new AlertMsg("idsAlert");
    alert->setDecision(decisionStr.c_str());
    alert->setPath(pathStr.c_str());
    alert->setPAttackRaw(rawProb);
    alert->setPAttackCalibrated(calProb);
    alert->setLatencyMs(latencyMs);
    alert->setEscalateFlag(decision == 2);
    alert->setTimestamp(simTime());

    send(alert, "decisionOut");
    delete msg;

    EV_DEBUG << "Route decision=" << decisionStr
             << " | path=" << pathStr
             << " | calProb=" << calProb << endl;
}

void ConfidenceRouter::finish()
{
    recordScalar("normalCount", normalCount_);
    recordScalar("attackCount", attackCount_);
    recordScalar("escalateCount", escalateCount_);
    recordScalar("fastPathCount", fastCount_);
    recordScalar("heavyPathCount", heavyCount_);
    recordScalar("expertOverrideCount", expertOverrideCount_);

    double total = normalCount_ + attackCount_ + escalateCount_;
    if (total > 0) {
        recordScalar("routingRatioFast",
            static_cast<double>(fastCount_) / (fastCount_ + heavyCount_));
    }

    EV_INFO << "ConfidenceRouter finished | NORMAL=" << normalCount_
            << " ATTACK=" << attackCount_
            << " ESCALATE=" << escalateCount_
            << " fast=" << fastCount_
            << " heavy=" << heavyCount_
            << " expertOverride=" << expertOverrideCount_ << endl;
}

} // namespace dpcrids
