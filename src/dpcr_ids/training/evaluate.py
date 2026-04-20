"""Evaluation helpers for saved predictions and in-memory outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dpcr_ids.training.metrics import binary_classification_report
from dpcr_ids.training.metrics import per_attack_type_report
from dpcr_ids.training.metrics import routing_ratio
from dpcr_ids.utils.fs import read_jsonl



def evaluate_predictions(
    labels: list[int],
    probabilities: list[float],
    threshold: float = 0.5,
    paths: list[str] | None = None,
    extra: dict[str, Any] | None = None,
    attack_types: list[str] | None = None,
) -> dict[str, Any]:
    merged_extra = dict(extra or {})
    if paths is not None:
        merged_extra["routing_ratio"] = routing_ratio(paths)
    if attack_types is not None:
        merged_extra["per_attack_type"] = per_attack_type_report(
            labels, probabilities, attack_types, threshold=threshold,
        )
    return binary_classification_report(labels, probabilities, threshold=threshold, extra=merged_extra)



def evaluate_prediction_rows(path: str | Path, threshold: float = 0.5) -> dict[str, Any]:
    rows = read_jsonl(path)
    labels = [int(row["label"]) for row in rows]
    probabilities = [float(row["probability"]) for row in rows]
    paths = [str(row.get("path", "fast")) for row in rows]
    attack_types_list = [str(row.get("attack_type", "unknown")) for row in rows]
    has_types = any(row.get("attack_type") is not None for row in rows)
    return evaluate_predictions(
        labels, probabilities, threshold=threshold, paths=paths,
        attack_types=attack_types_list if has_types else None,
    )

