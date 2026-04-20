// --------------------------------------------------------------------------
// ExpertOutput.msg — Expert module output (logit + embedding).
// OMNeT++ 6 compatible.
// --------------------------------------------------------------------------

namespace dpcrids;

message ExpertOutput
{
    string protocol;           // "can" or "ethernet"
    double logit;              // raw model logit
    double rawProb;            // sigmoid(logit)
    double calibratedProb;     // temperature-scaled probability
    double embedding[128];     // 128-dim feature embedding
    simtime_t timestamp;       // simulation time of the input data
}
