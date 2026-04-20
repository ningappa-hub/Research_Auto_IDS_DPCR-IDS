// --------------------------------------------------------------------------
// TemperatureScaler.h — Post-hoc calibration for binary classifier outputs.
// Mirrors dpcr_ids.training.calibration.TemperatureScaler
// --------------------------------------------------------------------------
#ifndef DPCR_IDS_TEMPERATURE_SCALER_H
#define DPCR_IDS_TEMPERATURE_SCALER_H

#include <cmath>

namespace dpcrids {

/**
 * Applies temperature scaling to convert raw logits/probabilities
 * into calibrated probabilities. Matches the Python TemperatureScaler.
 */
class TemperatureScaler {
public:
    explicit TemperatureScaler(double temperature = 1.0)
        : temperature_(temperature) {}

    double getTemperature() const { return temperature_; }

    /** Scale a raw logit by dividing by temperature. */
    double transformLogit(double logit) const {
        return logit / temperature_;
    }

    /** Convert a probability through logit-space temperature scaling. */
    double transformProbability(double probability) const {
        // Clamp to avoid log(0)
        probability = std::max(1e-7, std::min(probability, 1.0 - 1e-7));
        double logit = std::log(probability / (1.0 - probability));
        double scaledLogit = transformLogit(logit);
        return sigmoid(scaledLogit);
    }

    /** Standard sigmoid function. */
    static double sigmoid(double x) {
        return 1.0 / (1.0 + std::exp(-x));
    }

private:
    double temperature_;
};

} // namespace dpcrids

#endif // DPCR_IDS_TEMPERATURE_SCALER_H
