// --------------------------------------------------------------------------
// EthBusHub.cc — Forwards all incoming Ethernet frames to the single output.
// --------------------------------------------------------------------------
#include <omnetpp.h>
#include <sstream>

using namespace omnetpp;

namespace dpcrids {

class EthBusHub : public cSimpleModule {
protected:
    virtual void initialize() override {
        getDisplayString().setTagArg("t", 0, "ETH bus idle");
        getDisplayString().setTagArg("i", 1, "gray");
    }

    virtual void handleMessage(cMessage *msg) override {
        forwarded_++;
        if (forwarded_ % 250 == 0) {
            std::ostringstream status;
            status << "ETH bus n=" << forwarded_;
            getDisplayString().setTagArg("t", 0, status.str().c_str());
            getDisplayString().setTagArg("i", 1, "blue");
        }
        send(msg, "out");
    }

private:
    long forwarded_ = 0;
};

Define_Module(EthBusHub);

} // namespace dpcrids
