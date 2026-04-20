// --------------------------------------------------------------------------
// EthBusHub.ned — Merges multiple Ethernet sources into a single output.
// Simulates a simplified Ethernet switch. Replace with INET EthernetSwitch
// for realistic queuing and TSN behavior.
// --------------------------------------------------------------------------

package dpcrids.nodes;

simple EthBusHub
{
    parameters:
        int numInputs;
        @display("i=block/fork,darkcyan");

    gates:
        input in[numInputs];
        output out;
}
