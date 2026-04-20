// --------------------------------------------------------------------------
// CanExpertIDS.cc — Implementation of the CAN TCN expert module.
// --------------------------------------------------------------------------
#include "CanExpertIDS.h"
#include "../msg/CanFrameMsg_m.h"
#include "../msg/ExpertOutput_m.h"
#include <chrono>

namespace dpcrids {

Define_Module(CanExpertIDS);

void CanExpertIDS::initialize()
{
    windowSize_ = par("windowSize").intValue();
    stride_     = par("stride").intValue();

    // Load ONNX model
    std::string modelPath = par("onnxModelPath").stdstringValue();
    onnxModel_ = std::make_unique<OnnxInference>(modelPath, 1);

    // Load calibration temperature
    double temp = par("temperature").doubleValue();
    scaler_ = TemperatureScaler(temp);

    // Register statistics signals
    logitSignal_       = registerSignal("canLogit");
    calProbSignal_     = registerSignal("canCalProb");
    inferenceMsSignal_ = registerSignal("canInferenceMs");

    EV_INFO << "CanExpertIDS initialized | model=" << modelPath
            << " | temperature=" << temp
            << " | window=" << windowSize_
            << " | stride=" << stride_ << endl;
}

void CanExpertIDS::handleMessage(cMessage *msg)
{
    // Expect CanFrameMsg from the gateway
    CanFrameMsg *frameMsg = check_and_cast<CanFrameMsg *>(msg);

    // Convert to internal CanFrame struct
    CanFrame frame;
    frame.canId     = frameMsg->getCanId();
    frame.dlc       = frameMsg->getDlc();
    for (int i = 0; i < 8; i++) {
        frame.data[i] = frameMsg->getData(i);
    }
    frame.timestamp = simTime().dbl();

    frameBuffer_.push_back(frame);
    framesReceived_++;

    delete msg;

    // Check if we have a complete window
    if (static_cast<int>(frameBuffer_.size()) >= windowSize_) {
        // Extract the window
        std::vector<CanFrame> window(frameBuffer_.begin(),
                                      frameBuffer_.begin() + windowSize_);
        processWindow(window);

        // Slide by stride
        if (static_cast<int>(frameBuffer_.size()) > stride_) {
            frameBuffer_.erase(frameBuffer_.begin(),
                               frameBuffer_.begin() + stride_);
        } else {
            frameBuffer_.clear();
        }
    }
}

void CanExpertIDS::processWindow(const std::vector<CanFrame>& window)
{
    auto startTime = std::chrono::high_resolution_clock::now();

    // Step 1: Extract features → [16, windowSize] flat vector
    std::vector<float> features = FeatureExtractor::extractWindow(window);

    // Step 2: Run ONNX inference → logit + embedding
    // The ONNX model input shape is [1, 16, 100] (batch, channels, sequence)
    std::vector<int64_t> inputShape = {1, FeatureExtractor::NUM_FEATURES,
                                        static_cast<int64_t>(window.size())};
    std::vector<float> output = onnxModel_->run(features, inputShape);

    // output[0] = logit (scalar), output[1..128] = embedding (128-dim)
    // Note: The ONNX model exports forward() which outputs just the logit.
    // For the embedding, we need a dual-output model. For now, we run the
    // model and use the logit; the embedding comes from a second output head.

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

    // Step 3: Build ExpertOutput message → send to FusionIDS
    ExpertOutput *expertMsg = new ExpertOutput("canExpert");
    expertMsg->setProtocol("can");
    expertMsg->setLogit(logit);
    expertMsg->setCalibratedProb(calProb);
    expertMsg->setRawProb(rawProb);
    expertMsg->setTimestamp(simTime());

    // Pack embedding (128 values) from ONNX model output
    for (int i = 0; i < 128; i++) {
        // If ONNX model has dual output, output[1+i] is embedding
        // Otherwise, zero-fill (will be replaced with dual-output model)
        float embVal = (output.size() > static_cast<size_t>(1 + i)) ?
                        output[1 + i] : 0.0f;
        expertMsg->setEmbedding(i, embVal);
    }

    send(expertMsg, "expertOut");
    windowsProcessed_++;

    EV_DEBUG << "CAN window #" << windowsProcessed_
             << " | logit=" << logit
             << " | calProb=" << calProb
             << " | inferenceMs=" << inferenceMs << endl;
}

void CanExpertIDS::finish()
{
    EV_INFO << "CanExpertIDS finished | framesReceived=" << framesReceived_
            << " | windowsProcessed=" << windowsProcessed_ << endl;
    recordScalar("framesReceived", framesReceived_);
    recordScalar("windowsProcessed", windowsProcessed_);
}

} // namespace dpcrids
