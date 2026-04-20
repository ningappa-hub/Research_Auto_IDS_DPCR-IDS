// --------------------------------------------------------------------------
// CanBusHub.ned — Merges multiple CAN frame sources into a single output.
// Simulates a shared CAN bus medium. Replace with FiCo4OMNeT CanBus
// for realistic arbitration and timing.
// --------------------------------------------------------------------------

package dpcrids.nodes;

simple CanBusHub
{
    parameters:
        int numInputs;
        @display("i=block/fork,darkgreen");

    gates:
        input in[numInputs];
        output out;
}
