// --------------------------------------------------------------------------
// EthExpertIDS.cc — Implementation of the Ethernet CNN expert module.
// --------------------------------------------------------------------------
#include "EthExpertIDS.h"
#include "../msg/EthFrameMsg_m.h"
#include "../msg/ExpertOutput_m.h"
#include <chrono>
#include <algorithm>

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

    // Convert payload → [3, 32, 32] image tensor
    std::vector<float> imageTensor = payloadToImage(payload);

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

std::vector<float> EthExpertIDS::payloadToImage(const std::vector<uint8_t>& payload)
{
    int totalPixels = inChannels_ * frameHeight_ * frameWidth_;
    std::vector<float> image(totalPixels, 0.0f);

    // Map payload bytes into [3, 32, 32] tensor
    // Each channel gets payloadBytes_/3 consecutive bytes, normalized to [0, 1]
    int bytesPerChannel = frameHeight_ * frameWidth_;  // 32*32 = 1024
    int payloadLen = static_cast<int>(payload.size());

    for (int c = 0; c < inChannels_; c++) {
        for (int h = 0; h < frameHeight_; h++) {
            for (int w = 0; w < frameWidth_; w++) {
                int byteIdx = c * bytesPerChannel + h * frameWidth_ + w;
                int tensorIdx = c * (frameHeight_ * frameWidth_) + h * frameWidth_ + w;
                if (byteIdx < payloadLen) {
                    image[tensorIdx] = static_cast<float>(payload[byteIdx]) / 255.0f;
                }
                // else zero-padded (already initialized to 0)
            }
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
