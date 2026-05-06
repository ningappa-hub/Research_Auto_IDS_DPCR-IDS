// --------------------------------------------------------------------------
// ConfidenceRouter.cc — Routes fused probabilities through fast/heavy paths.
// Exact port of dpcr_ids.runtime.router.ConfidenceRouter
// --------------------------------------------------------------------------
#include "ConfidenceRouter.h"
#include "../msg/FusionResult_m.h"
#include "../msg/AlertMsg_m.h"
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <sstream>

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

    getDisplayString().setTagArg("t", 0, "Router idle");
    getDisplayString().setTagArg("i", 1, "gray");

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
    double alertRawProb = rawProb;
    double alertCalProb = calProb;

    int decision;    // 0=NORMAL, 1=ATTACK, 2=ESCALATE
    int pathType;    // 0=fast, 1=heavy
    std::string decisionStr;
    std::string pathStr;
    bool overrideUsed = false;

    // Expert-aware override: route primarily on the calibrated fusion probability.
    // The fusion model was retrained on real expert embeddings and is the most
    // reliable signal. The individual expert probabilities serve as a secondary
    // sanity check: if the ETH expert strongly predicts NORMAL (p_eth << tau_low)
    // AND the fusion output is also below the high threshold, we apply the override.
    //
    // NOTE: The CAN expert produces OOD-high probabilities for synthetic OMNeT++
    // traffic (the simulated random-walk payload differs from the real Car-Hacking
    // dataset statistics), so we do NOT require the CAN expert to be NORMAL.
    // This is a known simulation limitation documented in the paper.
    if (expertOverride_) {
        double ethProb = fusion->getEthRawProb();
        // If the ETH expert independently predicts NORMAL with high confidence
        // AND the fusion output is not a high-confidence ATTACK, override to NORMAL.
        // This correctly handles scenarios where CAN is OOD but ETH is reliable.
        if (ethProb <= tauLow_ && calProb < 0.97) {
            alertRawProb = ethProb;
            alertCalProb = ethProb;
            decision = 0;
            decisionStr = "NORMAL";
            pathType = 0;
            pathStr = "fast";
            normalCount_++;
            fastCount_++;
            expertOverrideCount_++;
            overrideUsed = true;

            EV_DEBUG << "Expert override: ETH NORMAL (p_eth=" << ethProb
                     << ", fusion_cal=" << calProb
                     << ") -> NORMAL override" << endl;

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

    const char *color = "orange";
    if (decisionStr == "ATTACK") {
        color = "red";
    } else if (decisionStr == "NORMAL") {
        color = "green";
    }
    if (decisionStr == "ESCALATE") {
        color = "yellow";
    }

    std::ostringstream status;
    status << decisionStr << " " << pathStr
           << " p=" << std::fixed << std::setprecision(2) << alertCalProb;
    if (overrideUsed) {
        status << " override";
    }
    getDisplayString().setTagArg("t", 0, status.str().c_str());
    getDisplayString().setTagArg("i", 1, color);

    // Build alert message
    AlertMsg *alert = new AlertMsg("idsAlert");
    alert->setDecision(decisionStr.c_str());
    alert->setPath(pathStr.c_str());
    alert->setPAttackRaw(alertRawProb);
    alert->setPAttackCalibrated(alertCalProb);
    alert->setLatencyMs(latencyMs);
    alert->setEscalateFlag(decision == 2);
    alert->setTimestamp(simTime());

    send(alert, "decisionOut");
    delete msg;

    EV_DEBUG << "Route decision=" << decisionStr
             << " | path=" << pathStr
             << " | alertCalProb=" << alertCalProb
             << " | fusionCalProb=" << calProb << endl;
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
