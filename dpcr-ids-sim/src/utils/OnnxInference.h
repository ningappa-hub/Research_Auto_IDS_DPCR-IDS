// --------------------------------------------------------------------------
// OnnxInference.h — ONNX Runtime wrapper for OMNeT++ IDS modules.
// Supports compilation with or without ONNX Runtime:
//   - With ONNX: links onnxruntime, runs real inference
//   - Without ONNX (DPCR_NO_ONNX): uses stub that returns fixed values
// --------------------------------------------------------------------------
#ifndef DPCR_IDS_ONNX_INFERENCE_H
#define DPCR_IDS_ONNX_INFERENCE_H

#include <string>
#include <vector>
#include <memory>
#include <iostream>
#include <cmath>

#ifndef DPCR_NO_ONNX
#include <onnxruntime_cxx_api.h>
#endif

namespace dpcrids {

class OnnxInference {
public:
    explicit OnnxInference(const std::string& modelPath, int numThreads = 1);
    ~OnnxInference() = default;

    OnnxInference(const OnnxInference&) = delete;
    OnnxInference& operator=(const OnnxInference&) = delete;

    /**
     * Run inference on a single sample.
     * @param inputData   flat vector of floats (row-major)
     * @param inputShape  shape dimensions, e.g. {1, 16, 100} for CAN
     * @return            flat output tensor values
     */
    std::vector<float> run(const std::vector<float>& inputData,
                           const std::vector<int64_t>& inputShape);

    const std::string& getModelPath() const { return modelPath_; }

private:
    std::string modelPath_;

#ifndef DPCR_NO_ONNX
    Ort::Env env_;
    Ort::SessionOptions sessionOptions_;
    std::unique_ptr<Ort::Session> session_;
    Ort::AllocatorWithDefaultOptions allocator_;
    std::string inputName_;
    std::vector<std::string> outputNames_;
#endif
};

} // namespace dpcrids

#endif // DPCR_IDS_ONNX_INFERENCE_H
