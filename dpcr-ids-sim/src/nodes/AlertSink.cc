// --------------------------------------------------------------------------
// AlertSink.cc — Collects gateway alerts for result analysis.
// --------------------------------------------------------------------------
#include <omnetpp.h>
#include <fstream>
#include "../msg/AlertMsg_m.h"

using namespace omnetpp;

namespace dpcrids {

class AlertSink : public cSimpleModule {
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

private:
    simsignal_t decisionSignal_;
    simsignal_t latencySignal_;
    std::string logFile_;
    std::ofstream logStream_;

    long totalAlerts_ = 0;
    long normalCount_ = 0;
    long attackCount_ = 0;
    long escalateCount_ = 0;
};

Define_Module(AlertSink);

void AlertSink::initialize()
{
    decisionSignal_ = registerSignal("alertDecision");
    latencySignal_  = registerSignal("alertLatencyMs");
    logFile_ = par("logFile").stdstringValue();

    logStream_.open(logFile_, std::ios::out | std::ios::trunc);
    if (logStream_.is_open()) {
        logStream_ << "simtime,decision,path,p_attack_raw,p_attack_calibrated,"
                   << "latency_ms,escalate" << std::endl;
    }
}

void AlertSink::handleMessage(cMessage *msg)
{
    AlertMsg *alert = check_and_cast<AlertMsg *>(msg);

    std::string decision = alert->getDecision();
    double latency = alert->getLatencyMs();

    // Map decision to int for statistics
    int decInt = 0;
    if (decision == "ATTACK") { decInt = 1; attackCount_++; }
    else if (decision == "ESCALATE") { decInt = 2; escalateCount_++; }
    else { normalCount_++; }

    emit(decisionSignal_, static_cast<long>(decInt));
    emit(latencySignal_, latency);

    // Write CSV log
    if (logStream_.is_open()) {
        logStream_ << alert->getTimestamp() << ","
                   << decision << ","
                   << alert->getPath() << ","
                   << alert->getPAttackRaw() << ","
                   << alert->getPAttackCalibrated() << ","
                   << latency << ","
                   << (alert->getEscalateFlag() ? "true" : "false")
                   << std::endl;
    }

    totalAlerts_++;
    delete msg;
}

void AlertSink::finish()
{
    if (logStream_.is_open()) {
        logStream_.close();
    }

    recordScalar("totalAlerts", totalAlerts_);
    recordScalar("normalAlerts", normalCount_);
    recordScalar("attackAlerts", attackCount_);
    recordScalar("escalateAlerts", escalateCount_);

    EV_INFO << "AlertSink: total=" << totalAlerts_
            << " NORMAL=" << normalCount_
            << " ATTACK=" << attackCount_
            << " ESCALATE=" << escalateCount_ << endl;
}

} // namespace dpcrids
