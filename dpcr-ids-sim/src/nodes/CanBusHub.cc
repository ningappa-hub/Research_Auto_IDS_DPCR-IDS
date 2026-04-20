// --------------------------------------------------------------------------
// CanBusHub.cc — Forwards all incoming CAN frames to the single output.
// A simple shared-medium model. In a real CAN bus, arbitration would
// introduce priority-based delays; use FiCo4OMNeT for that fidelity.
// --------------------------------------------------------------------------
#include <omnetpp.h>

using namespace omnetpp;

namespace dpcrids {

class CanBusHub : public cSimpleModule {
protected:
    virtual void handleMessage(cMessage *msg) override {
        // Forward the CAN frame to the single output (gateway)
        send(msg, "out");
    }
};

Define_Module(CanBusHub);

} // namespace dpcrids
