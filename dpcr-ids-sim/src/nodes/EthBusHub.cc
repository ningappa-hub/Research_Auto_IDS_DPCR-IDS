// --------------------------------------------------------------------------
// EthBusHub.cc — Forwards all incoming Ethernet frames to the single output.
// --------------------------------------------------------------------------
#include <omnetpp.h>

using namespace omnetpp;

namespace dpcrids {

class EthBusHub : public cSimpleModule {
protected:
    virtual void handleMessage(cMessage *msg) override {
        send(msg, "out");
    }
};

Define_Module(EthBusHub);

} // namespace dpcrids
