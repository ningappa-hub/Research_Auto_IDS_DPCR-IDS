// --------------------------------------------------------------------------
// EthExpertIDS.cc — Implementation of the Ethernet CNN expert module.
// --------------------------------------------------------------------------
#include "EthExpertIDS.h"
#include "../msg/EthFrameMsg_m.h"
#include "../msg/ExpertOutput_m.h"
#include <chrono>
#include <algorithm>
#include <iomanip>
#include <sstream>

namespace dpcrids {

Define_Module(EthExpertIDS);

void EthExpertIDS::initialize()
{
    payloadBytes_ = par("payloadBytes").intValue();
    frameHeight_  = par("frameHeight").intValue();
    frameWidth_   = par("frameWidth").intValue();
    inChannels_   = par("inChannels").intValue();

    std::string modelPath = par("onnxModelPath").stdstringValue();
    onnxModel_ = std::make_unique<OnnxInference>(modelPath, 1);

    double temp = par("temperature").doubleValue();
    scaler_ = TemperatureScaler(temp);

    logitSignal_       = registerSignal("ethLogit");
    calProbSignal_     = registerSignal("ethCalProb");
    inferenceMsSignal_ = registerSignal("ethInferenceMs");

    getDisplayString().setTagArg("t", 0, "ETH idle");
    getDisplayString().setTagArg("i", 1, "gray");

    EV_INFO << "EthExpertIDS initialized | model=" << modelPath
            << " | temperature=" << temp << endl;
}

void EthExpertIDS::handleMessage(cMessage *msg)
{
    EthFrameMsg *frameMsg = check_and_cast<EthFrameMsg *>(msg);

    // Extract payload bytes
    int payloadLen = frameMsg->getPayloadArraySize();
    std::vector<uint8_t> payload(payloadLen);
    for (int i = 0; i < payloadLen; i++) {
        payload[i] = frameMsg->getPayload(i);
    }

    delete msg;

    auto startTime = std::chrono::high_resolution_clock::now();

    // Convert payload → [3, 32, 32] image tensor matching Python pipeline
    std::vector<uint8_t> prevForDelta;
    if (hasPrevPayload_) {
        prevForDelta = prevPayload_;
    }
    std::vector<float> imageTensor = payloadToImage(payload, prevForDelta);

    // Update previous payload state
    prevPayload_ = payload;
    hasPrevPayload_ = true;

    // Run ONNX inference
    std::vector<int64_t> inputShape = {1, inChannels_, frameHeight_, frameWidth_};
    std::vector<float> output = onnxModel_->run(imageTensor, inputShape);

    float logit = output[0];
    double rawProb = TemperatureScaler::sigmoid(static_cast<double>(logit));
    double calProb = scaler_.transformProbability(rawProb);

    auto endTime = std::chrono::high_resolution_clock::now();
    double inferenceMs = std::chrono::duration<double, std::milli>(
        endTime - startTime).count();

    // Emit statistics
    emit(logitSignal_, static_cast<double>(logit));
    emit(calProbSignal_, calProb);
    emit(inferenceMsSignal_, inferenceMs);

    const char *color = "orange";
    if (calProb >= 0.85) {
        color = "red";
    } else if (calProb <= 0.15) {
        color = "green";
    }

    std::ostringstream status;
    status << "ETH p=" << std::fixed << std::setprecision(2) << calProb
           << " ms=" << std::setprecision(3) << inferenceMs;
    getDisplayString().setTagArg("t", 0, status.str().c_str());
    getDisplayString().setTagArg("i", 1, color);

    // Build expert output
    ExpertOutput *expertMsg = new ExpertOutput("ethExpert");
    expertMsg->setProtocol("ethernet");
    expertMsg->setLogit(logit);
    expertMsg->setCalibratedProb(calProb);
    expertMsg->setRawProb(rawProb);
    expertMsg->setTimestamp(simTime());

    for (int i = 0; i < 128; i++) {
        float embVal = (output.size() > static_cast<size_t>(1 + i)) ?
                        output[1 + i] : 0.0f;
        expertMsg->setEmbedding(i, embVal);
    }

    send(expertMsg, "expertOut");
    framesProcessed_++;
}

std::vector<float> EthExpertIDS::payloadToImage(const std::vector<uint8_t>& payload,
                                                  const std::vector<uint8_t>& prevPayload)
{
    int totalPixels = inChannels_ * frameHeight_ * frameWidth_;
    std::vector<float> image(totalPixels, 0.0f);

    // Pad payload to payloadBytes_
    std::vector<uint8_t> padded(payloadBytes_, 0);
    int copyLen = std::min(static_cast<int>(payload.size()), payloadBytes_);
    for (int i = 0; i < copyLen; i++) {
        padded[i] = payload[i];
    }

    // Pad previous payload to payloadBytes_
    std::vector<uint8_t> paddedPrev(payloadBytes_, 0);
    int prevCopyLen = std::min(static_cast<int>(prevPayload.size()), payloadBytes_);
    for (int i = 0; i < prevCopyLen; i++) {
        paddedPrev[i] = prevPayload[i];
    }

    // Build 3-channel image matching Python bytes_to_byte_image():
    //   Channel 0: value    — byte / 255.0
    //   Channel 1: delta    — clamp((current - previous) / 255.0, -1, 1)
    //   Channel 2: position — offset / payloadBytes_
    for (int h = 0; h < frameHeight_; h++) {
        for (int w = 0; w < frameWidth_; w++) {
            int byteIdx = h * frameWidth_ + w;

            float currentVal = static_cast<float>(padded[byteIdx]);
            float prevVal    = static_cast<float>(paddedPrev[byteIdx]);

            // Channel 0: value
            int ch0Idx = 0 * (frameHeight_ * frameWidth_) + h * frameWidth_ + w;
            image[ch0Idx] = currentVal / 255.0f;

            // Channel 1: delta (clamped to [-1, 1])
            int ch1Idx = 1 * (frameHeight_ * frameWidth_) + h * frameWidth_ + w;
            float delta = (currentVal - prevVal) / 255.0f;
            image[ch1Idx] = std::max(-1.0f, std::min(1.0f, delta));

            // Channel 2: position
            int ch2Idx = 2 * (frameHeight_ * frameWidth_) + h * frameWidth_ + w;
            image[ch2Idx] = static_cast<float>(byteIdx) / static_cast<float>(payloadBytes_);
        }
    }

    return image;
}

void EthExpertIDS::finish()
{
    EV_INFO << "EthExpertIDS finished | framesProcessed=" << framesProcessed_ << endl;
    recordScalar("framesProcessed", framesProcessed_);
}

} // namespace dpcrids
