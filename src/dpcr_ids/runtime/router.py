"""Confidence routing for protocol-specific fast and heavy paths."""

from __future__ import annotations

from dataclasses import dataclass

from dpcr_ids.exceptions import DataValidationError


@dataclass(slots=True)
class RouteResult:
    decision: str | None
    path: str
    p_attack_raw: float
    p_attack_calibrated: float


class ConfidenceRouter:
    def __init__(self, tau_low: float, tau_high: float) -> None:
        if not (0.0 <= tau_low <= tau_high <= 1.0):
            raise DataValidationError("Router thresholds must satisfy 0 <= tau_low <= tau_high <= 1")
        self.tau_low = tau_low
        self.tau_high = tau_high

    def route(
        self,
        p_attack_calibrated: float,
        p_attack_raw: float | None = None,
        expert_probs: dict[str, float] | None = None,
    ) -> RouteResult:
        raw = p_attack_calibrated if p_attack_raw is None else p_attack_raw

        # Expert-aware override: if ALL individual experts independently
        # predict NORMAL with high confidence, short-circuit to NORMAL
        # regardless of the fusion output.  This prevents false positives
        # when the fusion model has not seen sufficient joint-normal pairs.
        if expert_probs is not None and len(expert_probs) > 0:
            if all(p <= self.tau_low for p in expert_probs.values()):
                return RouteResult(
                    decision="NORMAL", path="fast",
                    p_attack_raw=raw, p_attack_calibrated=p_attack_calibrated,
                )

        if p_attack_calibrated >= self.tau_high:
            return RouteResult(decision="ATTACK", path="fast", p_attack_raw=raw, p_attack_calibrated=p_attack_calibrated)
        if p_attack_calibrated <= self.tau_low:
            return RouteResult(decision="NORMAL", path="fast", p_attack_raw=raw, p_attack_calibrated=p_attack_calibrated)
        return RouteResult(decision=None, path="heavy", p_attack_raw=raw, p_attack_calibrated=p_attack_calibrated)
