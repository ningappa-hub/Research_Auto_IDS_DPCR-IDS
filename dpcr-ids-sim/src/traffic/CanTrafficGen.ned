// --------------------------------------------------------------------------
// CanTrafficGen.ned — Normal CAN traffic generator (sensor ECU).
// --------------------------------------------------------------------------

package dpcrids.traffic;

simple CanTrafficGen
{
    parameters:
        double sendInterval @unit(s) = default(0.002s);  // ~500 msg/s at 500kbit/s
        int numCanIds = default(50);       // number of unique CAN IDs to cycle
        int startCanId = default(0x100);   // base CAN ID
        volatile int payloadLength = default(8);  // DLC
        @display("i=block/source,green");

    gates:
        output canOut;
}
