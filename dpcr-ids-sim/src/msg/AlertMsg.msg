// --------------------------------------------------------------------------
// AlertMsg.msg — IDS alert from router or gateway aggregator.
// --------------------------------------------------------------------------

namespace dpcrids;

message AlertMsg
{
    string decision;             // "NORMAL", "ATTACK", "ESCALATE"
    string path;                 // "fast", "heavy", "fail_open", "gateway"
    double pAttackRaw;
    double pAttackCalibrated;
    double latencyMs;
    bool escalateFlag;
    simtime_t timestamp;
}
