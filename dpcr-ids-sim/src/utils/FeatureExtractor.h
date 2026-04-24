// --------------------------------------------------------------------------
// FeatureExtractor.h — Computes the 16 CAN features from raw frame windows.
// Mirrors the Python CAN preprocessing pipeline exactly, including z-score
// normalization fitted on the training set.
// --------------------------------------------------------------------------
#ifndef DPCR_IDS_FEATURE_EXTRACTOR_H
#define DPCR_IDS_FEATURE_EXTRACTOR_H

#include <vector>
#include <cstdint>
#include <unordered_map>
#include <deque>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <iostream>

namespace dpcrids {

/**
 * A single raw CAN frame as captured from the bus.
 */
struct CanFrame {
    uint32_t canId;
    uint8_t  dlc;
    uint8_t  data[8];    // d0..d7
    double   timestamp;  // simulation time in seconds
};

/**
 * Z-score normalization parameters fitted on the training set.
 * Loaded from the CAN qa_report.json or a dedicated normalization file.
 */
struct ZScoreParams {
    std::vector<float> means;
    std::vector<float> stds;
    bool loaded = false;

    /**
     * Load normalization parameters from a JSON file containing
     * "normalization": { "means": [...], "stds": [...] }.
     * Uses a simple parser to avoid external JSON library dependency.
     */
    static ZScoreParams loadFromFile(const std::string& path) {
        ZScoreParams params;
        std::ifstream file(path);
        if (!file.is_open()) {
            std::cerr << "[FeatureExtractor] WARNING: Cannot open normalization file: "
                      << path << " — features will NOT be z-score normalized." << std::endl;
            return params;
        }

        std::string content((std::istreambuf_iterator<char>(file)),
                             std::istreambuf_iterator<char>());
        file.close();

        params.means = parseJsonArray(content, "\"means\"");
        params.stds  = parseJsonArray(content, "\"stds\"");

        if (params.means.size() == 16 && params.stds.size() == 16) {
            params.loaded = true;
            std::cout << "[FeatureExtractor] Loaded z-score normalization (16 channels) from: "
                      << path << std::endl;
        } else {
            std::cerr << "[FeatureExtractor] WARNING: Expected 16 means and 16 stds, got "
                      << params.means.size() << " means and " << params.stds.size()
                      << " stds — features will NOT be z-score normalized." << std::endl;
        }
        return params;
    }

private:
    /**
     * Minimal JSON array parser: finds `key: [...]` and extracts float values.
     */
    static std::vector<float> parseJsonArray(const std::string& json,
                                              const std::string& key) {
        std::vector<float> values;
        auto keyPos = json.find(key);
        if (keyPos == std::string::npos) return values;

        auto bracketStart = json.find('[', keyPos);
        if (bracketStart == std::string::npos) return values;

        auto bracketEnd = json.find(']', bracketStart);
        if (bracketEnd == std::string::npos) return values;

        std::string arrayContent = json.substr(bracketStart + 1,
                                                bracketEnd - bracketStart - 1);

        std::istringstream stream(arrayContent);
        std::string token;
        while (std::getline(stream, token, ',')) {
            // Trim whitespace
            size_t start = token.find_first_not_of(" \t\n\r");
            if (start == std::string::npos) continue;
            size_t end = token.find_last_not_of(" \t\n\r");
            std::string trimmed = token.substr(start, end - start + 1);
            if (!trimmed.empty()) {
                try {
                    values.push_back(std::stof(trimmed));
                } catch (...) {
                    // skip non-numeric tokens
                }
            }
        }
        return values;
    }
};

/**
 * Extracts the 16 engineered features from a window of CAN frames.
 *
 * Feature vector per frame (matching Python pipeline):
 *   [0]  can_id           — normalized CAN arbitration ID
 *   [1]  dlc              — data length code
 *   [2-9] d0..d7          — payload bytes (normalized 0..1)
 *   [10] iat_same_id      — inter-arrival time for same CAN ID
 *   [11] payload_entropy  — Shannon entropy of the 8 payload bytes
 *   [12] payload_delta_mean — mean absolute difference between consecutive payloads
 *   [13] msg_freq_hz      — message frequency for this CAN ID over the window
 *   [14] local_busload    — total frames in window / window duration
 *   [15] bitflip_ratio    — fraction of bits flipped vs previous frame with same ID
 */
class FeatureExtractor {
public:
    static constexpr int NUM_FEATURES = 16;
    static constexpr int WINDOW_SIZE  = 100;
    static constexpr int STRIDE       = 50;

    /**
     * Extract feature matrix [NUM_FEATURES x windowSize] from a window of frames.
     * Returns data in column-major order matching PyTorch Conv1d layout [C, L].
     * Raw features (no z-score normalization applied).
     */
    static std::vector<float> extractWindow(const std::vector<CanFrame>& window) {
        int W = static_cast<int>(window.size());
        // Output: [16, W] in row-major (feature-first)
        std::vector<float> features(NUM_FEATURES * W, 0.0f);

        // Pre-compute per-ID statistics
        std::unordered_map<uint32_t, double> lastTimestamp;
        std::unordered_map<uint32_t, std::vector<uint8_t>> lastPayload;
        std::unordered_map<uint32_t, int> idCounts;

        // Count IDs for frequency
        for (const auto& f : window) {
            idCounts[f.canId]++;
        }

        double windowDuration = 0.0;
        if (W > 1) {
            windowDuration = window.back().timestamp - window.front().timestamp;
        }
        double busload = (windowDuration > 1e-9) ?
            static_cast<double>(W) / windowDuration : 0.0;

        for (int i = 0; i < W; i++) {
            const CanFrame& frame = window[i];
            int col = i;

            // [0] can_id — normalize to [0, 1] assuming max 0x7FF (standard CAN)
            features[0 * W + col] = static_cast<float>(frame.canId) / 2047.0f;

            // [1] dlc
            features[1 * W + col] = static_cast<float>(frame.dlc) / 8.0f;

            // [2..9] d0..d7
            for (int b = 0; b < 8; b++) {
                features[(2 + b) * W + col] = static_cast<float>(frame.data[b]) / 255.0f;
            }

            // [10] iat_same_id
            double iat = 0.0;
            if (lastTimestamp.count(frame.canId)) {
                iat = frame.timestamp - lastTimestamp[frame.canId];
            }
            lastTimestamp[frame.canId] = frame.timestamp;
            features[10 * W + col] = static_cast<float>(iat);

            // [11] payload_entropy (Shannon entropy of 8 bytes)
            features[11 * W + col] = computeEntropy(frame.data, 8);

            // [12] payload_delta_mean (vs previous frame with same ID)
            float deltaMean = 0.0f;
            if (lastPayload.count(frame.canId)) {
                const auto& prev = lastPayload[frame.canId];
                float sum = 0.0f;
                for (int b = 0; b < 8; b++) {
                    sum += std::abs(static_cast<float>(frame.data[b]) -
                                    static_cast<float>(prev[b]));
                }
                deltaMean = sum / 8.0f / 255.0f;
            }
            lastPayload[frame.canId] = std::vector<uint8_t>(frame.data, frame.data + 8);
            features[12 * W + col] = deltaMean;

            // [13] msg_freq_hz
            double freq = (windowDuration > 1e-9) ?
                static_cast<double>(idCounts[frame.canId]) / windowDuration : 0.0;
            features[13 * W + col] = static_cast<float>(freq);

            // [14] local_busload
            features[14 * W + col] = static_cast<float>(busload);

            // [15] bitflip_ratio — placeholder, computed in second pass below
            features[15 * W + col] = 0.0f;
        }

        // Second pass for bitflip_ratio (needs previous payload before overwrite)
        {
            std::unordered_map<uint32_t, std::vector<uint8_t>> prevPayload;
            for (int i = 0; i < W; i++) {
                const CanFrame& frame = window[i];
                float ratio = 0.0f;
                if (prevPayload.count(frame.canId)) {
                    const auto& prev = prevPayload[frame.canId];
                    int totalBits = 64; // 8 bytes * 8 bits
                    int flipped = 0;
                    for (int b = 0; b < 8; b++) {
                        uint8_t xored = frame.data[b] ^ prev[b];
                        // popcount
                        while (xored) {
                            flipped += xored & 1;
                            xored >>= 1;
                        }
                    }
                    ratio = static_cast<float>(flipped) / static_cast<float>(totalBits);
                }
                prevPayload[frame.canId] = std::vector<uint8_t>(frame.data, frame.data + 8);
                features[15 * W + i] = ratio;
            }
        }

        return features;
    }

    /**
     * Extract features AND apply z-score normalization.
     * This matches the full Python preprocessing pipeline:
     *   raw features → z-score normalize using training set statistics.
     *
     * @param window   The window of CAN frames to extract features from.
     * @param zscore   Z-score parameters loaded from the training QA report.
     * @return Normalized feature matrix [NUM_FEATURES x windowSize].
     */
    static std::vector<float> extractWindowNormalized(
        const std::vector<CanFrame>& window,
        const ZScoreParams& zscore)
    {
        std::vector<float> features = extractWindow(window);

        if (!zscore.loaded) {
            return features;  // Fall back to raw features if normalization unavailable
        }

        int W = static_cast<int>(window.size());
        for (int c = 0; c < NUM_FEATURES; c++) {
            float mean = zscore.means[c];
            float std  = zscore.stds[c];
            if (std < 1e-9f) std = 1.0f;  // Guard against zero std
            for (int i = 0; i < W; i++) {
                features[c * W + i] = (features[c * W + i] - mean) / std;
            }
        }

        return features;
    }

private:
    /** Shannon entropy of a byte array. */
    static float computeEntropy(const uint8_t* data, int len) {
        int counts[256] = {};
        for (int i = 0; i < len; i++) {
            counts[data[i]]++;
        }
        float entropy = 0.0f;
        for (int i = 0; i < 256; i++) {
            if (counts[i] > 0) {
                float p = static_cast<float>(counts[i]) / static_cast<float>(len);
                entropy -= p * std::log2(p);
            }
        }
        return entropy;
    }
};

} // namespace dpcrids

#endif // DPCR_IDS_FEATURE_EXTRACTOR_H
