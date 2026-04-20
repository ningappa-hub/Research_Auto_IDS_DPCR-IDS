// --------------------------------------------------------------------------
// CanFrameMsg.msg — CAN bus frame message definition (OMNeT++ 6 compatible).
// --------------------------------------------------------------------------

namespace dpcrids;

message CanFrameMsg
{
    int canId;
    int dlc;
    int data[8];             // payload bytes d0..d7 (0-255)
    int label = -1;          // ground truth: 0=normal, 1=attack, -1=unknown
    string attackType = "";  // "normal", "dos", "fuzzy", "gear", "rpm"
}
