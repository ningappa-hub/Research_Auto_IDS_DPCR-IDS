// --------------------------------------------------------------------------
// FusionIDS.cc — Implementation of the late fusion head.
// --------------------------------------------------------------------------
#include "FusionIDS.h"
#include "../msg/ExpertOutput_m.h"
#include "../msg/FusionResult_m.h"
#include <chrono>

namespace dpcrids {

Define_Module(FusionIDS);

void FusionIDS::initialize()
{
    numExperts_ = par("numExperts").intValue();
    expertDim_  = par("expertDim").intValue();
    bucketMs_   = par("bucketMs").doubleValue();

    std::string modelPath = par("onnxModelPath").stdstringValue();
    onnxModel_ = std::make_unique<OnnxInference>(modelPath, 1);

    double temp = par("temperature").doubleValue();
    scaler_ = TemperatureScaler(temp);

    fusionLogitSignal_       = registerSignal("fusionLogit");
    fusionCalProbSignal_     = registerSignal("fusionCalProb");
    fusionInferenceMsSignal_ = registerSignal("fusionInferenceMs");

    pendingCan_.valid = false;
    pendingEth_.valid = false;

    EV_INFO << "FusionIDS initialized | model=" << modelPath
            << " | temperature=" << temp
            << " | bucketMs=" << bucketMs_ << endl;
}

void FusionIDS::handleMessage(cMessage *msg)
{
    ExpertOutput *expert = check_and_cast<ExpertOutput *>(msg);

    std::string protocol = expert->getProtocol();

    ExpertData data;
    data.logit   = expert->getLogit();
    data.rawProb = expert->getRawProb();
    data.calProb = expert->getCalibratedProb();
    data.timestamp = expert->getTimestamp();
    data.embedding.resize(128);
    for (int i = 0; i < 128; i++) {
        data.embedding[i] = expert->getEmbedding(i);
    }
    data.valid = true;

    if (protocol == "can") {
        pendingCan_ = data;
    } else if (protocol == "ethernet") {
        pendingEth_ = data;
    } else {
        EV_WARN << "FusionIDS: unknown protocol '" << protocol << "'" << endl;
    }

    delete msg;

    // Try to pair and fuse
    tryFusion();
}

bool FusionIDS::withinBucket(simtime_t t1, simtime_t t2)
{
    double diffMs = std::abs((t1 - t2).dbl()) * 1000.0;
    return diffMs <= bucketMs_;
}

void FusionIDS::tryFusion()
{
    if (!pendingCan_.valid || !pendingEth_.valid)
        return;

    if (!withinBucket(pendingCan_.timestamp, pendingEth_.timestamp)) {
        // Discard the older one
        if (pendingCan_.timestamp < pendingEth_.timestamp) {
            pendingCan_.valid = false;
        } else {
            pendingEth_.valid = false;
        }
        return;
    }

    auto startTime = std::chrono::high_resolution_clock::now();

    // Stack expert outputs → [1, 2, 129] tensor
    // Expert order: [can, ethernet] matching Python pipeline
    std::vector<float> fusionInput(numExperts_ * expertDim_);

    // CAN expert: [logit, emb0, emb1, ..., emb127]
    fusionInput[0] = pendingCan_.logit;
    for (int i = 0; i < 128; i++) {
        fusionInput[1 + i] = pendingCan_.embedding[i];
    }

    // Ethernet expert: [logit, emb0, emb1, ..., emb127]
    fusionInput[expertDim_ + 0] = pendingEth_.logit;
    for (int i = 0; i < 128; i++) {
        fusionInput[expertDim_ + 1 + i] = pendingEth_.embedding[i];
    }

    // Run fusion ONNX model: input [1, 2, 129] → output logit
    std::vector<int64_t> inputShape = {1, numExperts_, expertDim_};
    std::vector<float> output = onnxModel_->run(fusionInput, inputShape);

    float fusionLogit = output[0];
    double rawProb = TemperatureScaler::sigmoid(static_cast<double>(fusionLogit));
    double calProb = scaler_.transformProbability(rawProb);

    auto endTime = std::chrono::high_resolution_clock::now();
    double inferenceMs = std::chrono::duration<double, std::milli>(
        endTime - startTime).count();

    // Emit statistics
    emit(fusionLogitSignal_, static_cast<double>(fusionLogit));
    emit(fusionCalProbSignal_, calProb);
    emit(fusionInferenceMsSignal_, inferenceMs);

    // Build FusionResult and send to Router
    FusionResult *result = new FusionResult("fusionResult");
    result->setLogit(fusionLogit);
    result->setRawProb(rawProb);
    result->setCalibratedProb(calProb);
    result->setCanRawProb(pendingCan_.rawProb);
    result->setEthRawProb(pendingEth_.rawProb);
    result->setTimestamp(simTime());

    send(result, "fusionOut");
    fusionsPaired_++;

    // Clear pending
    pendingCan_.valid = false;
    pendingEth_.valid = false;
}

void FusionIDS::finish()
{
    EV_INFO << "FusionIDS finished | fusionsPaired=" << fusionsPaired_ << endl;
    recordScalar("fusionsPaired", fusionsPaired_);
}

} // namespace dpcrids
