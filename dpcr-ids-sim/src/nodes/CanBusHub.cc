// --------------------------------------------------------------------------
// CanBusHub.cc — Forwards all incoming CAN frames to the single output.
// A simple shared-medium model. In a real CAN bus, arbitration would
// introduce priority-based delays; use FiCo4OMNeT for that fidelity.
// --------------------------------------------------------------------------
#include <omnetpp.h>
#include <sstream>

using namespace omnetpp;

namespace dpcrids {

class CanBusHub : public cSimpleModule {
protected:
    virtual void initialize() override {
        getDisplayString().setTagArg("t", 0, "CAN bus idle");
        getDisplayString().setTagArg("i", 1, "gray");
    }

    virtual void handleMessage(cMessage *msg) override {
        // Forward the CAN frame to the single output (gateway)
        forwarded_++;
        if (forwarded_ % 250 == 0) {
            std::ostringstream status;
            status << "CAN bus n=" << forwarded_;
            getDisplayString().setTagArg("t", 0, status.str().c_str());
            getDisplayString().setTagArg("i", 1, "green");
        }
        send(msg, "out");
    }

private:
    long forwarded_ = 0;
};

Define_Module(CanBusHub);

} // namespace dpcrids
