// --------------------------------------------------------------------------
// EthTrafficGen.ned — Normal Automotive Ethernet traffic generator.
// --------------------------------------------------------------------------

package dpcrids.traffic;

simple EthTrafficGen
{
    parameters:
        double sendInterval @unit(s) = default(0.001s);  // 1000 frames/s
        volatile int payloadLength = default(512);        // typical SOME/IP payload
        int maxPayloadLength = default(1500);
        @display("i=block/source,cyan");

    gates:
        output ethOut;
}
