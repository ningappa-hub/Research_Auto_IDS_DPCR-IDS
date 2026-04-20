// --------------------------------------------------------------------------
// OnnxInference.cc — Conditional build: real ONNX Runtime or stub mode.
// --------------------------------------------------------------------------
#include "OnnxInference.h"
#include <stdexcept>
#include <numeric>
#include <cstdlib>

namespace dpcrids {

#ifdef DPCR_NO_ONNX
// ==========================================================================
// STUB MODE — No ONNX Runtime required. Returns synthetic outputs.
// Use this to validate the simulation structure before integrating ONNX.
// ==========================================================================

OnnxInference::OnnxInference(const std::string& modelPath, int numThreads)
    : modelPath_(modelPath)
{
    std::cout << "[OnnxInference-STUB] Model path registered (not loaded): "
              << modelPath << std::endl;
}

std::vector<float> OnnxInference::run(const std::vector<float>& inputData,
                                       const std::vector<int64_t>& inputShape)
{
    // Determine output size from model type based on path
    // Compute a simple deterministic "score" from input data
    float inputSum = 0.0f;
    int count = 0;
    for (size_t i = 0; i < std::min(inputData.size(), (size_t)100); i++) {
        inputSum += inputData[i];
        count++;
    }
    float meanVal = (count > 0) ? inputSum / count : 0.0f;

    // Generate a pseudo-logit based on input statistics
    // This gives a deterministic but data-dependent output
    float logit = (meanVal - 0.5f) * 4.0f;  // roughly [-2, 2] range

    if (modelPath_.find("fusion") != std::string::npos) {
        // Fusion model: single logit output
        return {logit};
    } else {
        // Expert models (CAN/ETH): logit + 128-dim embedding
        std::vector<float> output(129);
        output[0] = logit;
        for (int i = 1; i < 129; i++) {
            // Deterministic pseudo-embedding
            output[i] = std::sin(static_cast<float>(i) * meanVal * 0.1f) * 0.5f;
        }
        return output;
    }
}

#else
// ==========================================================================
// REAL MODE — Uses ONNX Runtime for actual model inference.
// ==========================================================================

OnnxInference::OnnxInference(const std::string& modelPath, int numThreads)
    : modelPath_(modelPath),
      env_(ORT_LOGGING_LEVEL_WARNING, "dpcrids")
{
    sessionOptions_.SetIntraOpNumThreads(numThreads);
    sessionOptions_.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);

    session_ = std::make_unique<Ort::Session>(env_, modelPath.c_str(), sessionOptions_);

    // Cache input name
    {
        auto namePtr = session_->GetInputNameAllocated(0, allocator_);
        inputName_ = std::string(namePtr.get());
    }

    // Cache all output names (may have 1 or 2 outputs)
    size_t numOutputs = session_->GetOutputCount();
    for (size_t i = 0; i < numOutputs; i++) {
        auto namePtr = session_->GetOutputNameAllocated(i, allocator_);
        outputNames_.push_back(std::string(namePtr.get()));
    }

    std::cout << "[OnnxInference] Loaded model: " << modelPath
              << " | input='" << inputName_
              << "' | outputs=" << numOutputs << std::endl;
}

std::vector<float> OnnxInference::run(const std::vector<float>& inputData,
                                       const std::vector<int64_t>& inputShape)
{
    Ort::MemoryInfo memInfo = Ort::MemoryInfo::CreateCpu(
        OrtArenaAllocator, OrtMemTypeDefault);

    Ort::Value inputTensor = Ort::Value::CreateTensor<float>(
        memInfo,
        const_cast<float*>(inputData.data()),
        inputData.size(),
        inputShape.data(),
        inputShape.size()
    );

    const char* inputNames[] = { inputName_.c_str() };

    // Build output name pointers
    std::vector<const char*> outputNamePtrs;
    for (const auto& name : outputNames_) {
        outputNamePtrs.push_back(name.c_str());
    }

    auto outputTensors = session_->Run(
        Ort::RunOptions{nullptr},
        inputNames, &inputTensor, 1,
        outputNamePtrs.data(), outputNamePtrs.size()
    );

    // Concatenate all output tensors into a single flat vector
    std::vector<float> result;
    for (size_t i = 0; i < outputTensors.size(); i++) {
        float* data = outputTensors[i].GetTensorMutableData<float>();
        auto info = outputTensors[i].GetTensorTypeAndShapeInfo();
        size_t count = info.GetElementCount();
        result.insert(result.end(), data, data + count);
    }

    return result;
}

#endif // DPCR_NO_ONNX

} // namespace dpcrids
