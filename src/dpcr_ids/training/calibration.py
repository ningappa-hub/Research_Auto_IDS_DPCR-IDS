"""Temperature scaling for binary classifiers."""

from __future__ import annotations

import math
from dataclasses import dataclass

from dpcr_ids.training.metrics import expected_calibration_error
from dpcr_ids.training.metrics import negative_log_likelihood_from_logits
from dpcr_ids.training.metrics import sigmoid
from dpcr_ids.types import CalibrationArtifact


@dataclass(slots=True)
class TemperatureScaler:
    temperature: float = 1.0

    def transform_logit(self, logit: float) -> float:
        return logit / self.temperature

    def transform_probability(self, probability: float) -> float:
        probability = min(max(probability, 1e-7), 1 - 1e-7)
        logit = math.log(probability / (1 - probability))
        return sigmoid(self.transform_logit(logit))



def fit_temperature_from_logits(
    logits: list[float],
    labels: list[int],
    min_temp: float = 0.5,
    max_temp: float = 10.0,
    step: float = 0.05,
) -> tuple[TemperatureScaler, CalibrationArtifact]:
    best_temp = 1.0
    best_nll = negative_log_likelihood_from_logits(logits, labels, temperature=1.0)
    before_probs = [sigmoid(logit) for logit in logits]
    ece_before = expected_calibration_error(before_probs, labels)

    candidate = min_temp
    while candidate <= max_temp + 1e-9:
        nll = negative_log_likelihood_from_logits(logits, labels, temperature=candidate)
        if nll < best_nll:
            best_nll = nll
            best_temp = round(candidate, 4)
        candidate += step

    scaler = TemperatureScaler(best_temp)
    after_probs = [scaler.transform_probability(probability) for probability in before_probs]
    artifact = CalibrationArtifact(
        protocol="unknown",
        temperature=scaler.temperature,
        ece_before=ece_before,
        ece_after=expected_calibration_error(after_probs, labels),
    )
    return scaler, artifact
