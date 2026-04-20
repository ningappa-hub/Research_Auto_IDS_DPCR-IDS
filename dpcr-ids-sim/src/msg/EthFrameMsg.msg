// --------------------------------------------------------------------------
// EthFrameMsg.msg — Automotive Ethernet frame message (OMNeT++ 6 compatible).
// --------------------------------------------------------------------------

namespace dpcrids;

message EthFrameMsg
{
    int payload[];           // variable-length payload bytes (0-255)
    int payloadLength;
    string srcAddress = "";
    string dstAddress = "";
    int label = -1;          // ground truth: 0=normal, 1=attack
    string attackType = "";
    string protocol = "";    // e.g. "SOME/IP", "DoIP", "AVB"
}
