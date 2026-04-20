// --------------------------------------------------------------------------
// FusionResult.msg — Fused decision from late fusion head.
// OMNeT++ 6 compatible.
// --------------------------------------------------------------------------

namespace dpcrids;

message FusionResult
{
    double logit;              // fused logit
    double rawProb;            // sigmoid(fused logit)
    double calibratedProb;     // temperature-scaled fused probability
    double canRawProb;         // CAN expert's raw probability
    double ethRawProb;         // Ethernet expert's raw probability
    simtime_t timestamp;
}
