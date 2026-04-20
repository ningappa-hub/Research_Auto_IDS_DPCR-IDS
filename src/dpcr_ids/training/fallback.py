"""Protocol-specific fallback model utilities."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dpcr_ids.utils.deps import require_dependency
from dpcr_ids.utils.fs import ensure_dir


@dataclass(slots=True)
class FallbackDecision:
    decision: str
    probability: float
    escalate: bool



def extract_uncertain_indices(probabilities: list[float], tau_low: float, tau_high: float) -> list[int]:
    return [index for index, probability in enumerate(probabilities) if tau_low < probability < tau_high]



def fallback_uncertainty_decision(probability: float, low: float = 0.3, high: float = 0.7) -> FallbackDecision:
    if low < probability < high:
        return FallbackDecision(decision="ESCALATE", probability=probability, escalate=True)
    return FallbackDecision(decision="ATTACK" if probability >= high else "NORMAL", probability=probability, escalate=False)


class ProtocolFallbackModel:
    def __init__(self, n_estimators: int = 200, max_depth: int = 12, class_weight: str = "balanced") -> None:
        sklearn_ensemble = require_dependency("sklearn.ensemble")
        self.model = sklearn_ensemble.RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            class_weight=class_weight,
            random_state=42,
        )

    def fit(self, features: list[list[float]], labels: list[int]) -> None:
        self.model.fit(features, labels)

    def predict_probability(self, feature: list[float]) -> float:
        probabilities = self.model.predict_proba([feature])[0]
        classes = list(getattr(self.model, "classes_", []))
        if len(classes) == 1:
            return 1.0 if int(classes[0]) == 1 else 0.0
        if 1 not in classes:
            return 0.0
        attack_index = classes.index(1)
        return float(probabilities[attack_index])

    def predict_decision(self, feature: list[float], low: float = 0.3, high: float = 0.7) -> FallbackDecision:
        return fallback_uncertainty_decision(self.predict_probability(feature), low=low, high=high)

    def save(self, path: str | Path) -> str:
        target = Path(path)
        ensure_dir(target.parent)
        with target.open("wb") as handle:
            pickle.dump(self.model, handle)
        return str(target)

    @classmethod
    def load(cls, path: str | Path) -> "ProtocolFallbackModel":
        target = Path(path)
        with target.open("rb") as handle:
            model = pickle.load(handle)
        instance = object.__new__(cls)
        instance.model = model
        return instance
