"""Metrics for binary IDS evaluation."""

from __future__ import annotations

import math
from typing import Any
from typing import Iterable


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)



def binary_predictions(probabilities: Iterable[float], threshold: float = 0.5) -> list[int]:
    return [1 if probability >= threshold else 0 for probability in probabilities]



def binary_confusion(labels: Iterable[int], predictions: Iterable[int]) -> dict[str, int]:
    tp = fp = tn = fn = 0
    for label, prediction in zip(labels, predictions):
        if label == 1 and prediction == 1:
            tp += 1
        elif label == 0 and prediction == 1:
            fp += 1
        elif label == 0 and prediction == 0:
            tn += 1
        else:
            fn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}



def precision_recall_f1(labels: Iterable[int], predictions: Iterable[int]) -> dict[str, float]:
    confusion = binary_confusion(labels, predictions)
    tp = confusion["tp"]
    fp = confusion["fp"]
    fn = confusion["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}



def false_positive_rate(labels: Iterable[int], predictions: Iterable[int]) -> float:
    confusion = binary_confusion(labels, predictions)
    fp = confusion["fp"]
    tn = confusion["tn"]
    return fp / (fp + tn) if (fp + tn) else 0.0



def expected_calibration_error(probabilities: list[float], labels: list[int], n_bins: int = 15) -> float:
    if not probabilities:
        return 0.0
    bin_totals = [0] * n_bins
    bin_correct = [0] * n_bins
    bin_confidence = [0.0] * n_bins

    for probability, label in zip(probabilities, labels):
        index = min(int(probability * n_bins), n_bins - 1)
        bin_totals[index] += 1
        bin_confidence[index] += probability
        bin_correct[index] += int((probability >= 0.5) == bool(label))

    total = len(probabilities)
    ece = 0.0
    for index in range(n_bins):
        if bin_totals[index] == 0:
            continue
        accuracy = bin_correct[index] / bin_totals[index]
        confidence = bin_confidence[index] / bin_totals[index]
        ece += (bin_totals[index] / total) * abs(accuracy - confidence)
    return ece



def negative_log_likelihood_from_logits(logits: list[float], labels: list[int], temperature: float = 1.0) -> float:
    total = 0.0
    for logit, label in zip(logits, labels):
        probability = sigmoid(logit / temperature)
        probability = min(max(probability, 1e-7), 1 - 1e-7)
        total += -(label * math.log(probability) + (1 - label) * math.log(1 - probability))
    return total / max(len(labels), 1)



def routing_ratio(paths: Iterable[str]) -> float:
    path_list = list(paths)
    if not path_list:
        return 0.0
    heavy = sum(1 for path in path_list if path == "heavy")
    return heavy / len(path_list)



def safe_auc_metrics(labels: list[int], probabilities: list[float]) -> dict[str, float | None]:
    try:
        from sklearn.metrics import average_precision_score  # type: ignore
        from sklearn.metrics import roc_auc_score  # type: ignore
    except ModuleNotFoundError:
        return {"auc_pr": None, "auc_roc": None}

    if len(set(labels)) < 2:
        return {"auc_pr": None, "auc_roc": None}
    return {
        "auc_pr": float(average_precision_score(labels, probabilities)),
        "auc_roc": float(roc_auc_score(labels, probabilities)),
    }



def binary_classification_report(
    labels: list[int],
    probabilities: list[float],
    threshold: float = 0.5,
    n_bins: int = 15,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    predictions = binary_predictions(probabilities, threshold=threshold)
    prf = precision_recall_f1(labels, predictions)
    report: dict[str, Any] = {
        **binary_confusion(labels, predictions),
        **prf,
        "dr": prf["recall"],
        "fpr": false_positive_rate(labels, predictions),
        "ece": expected_calibration_error(probabilities, labels, n_bins=n_bins),
    }
    report.update(safe_auc_metrics(labels, probabilities))
    if extra:
        report.update(extra)
    return report



def per_attack_type_report(
    labels: list[int],
    probabilities: list[float],
    attack_types: list[str],
    threshold: float = 0.5,
) -> dict[str, dict[str, Any]]:
    """Binary classification report broken down by attack type.

    Returns a dict keyed by attack_type, where each value is a metrics dict
    containing precision, recall, f1, fpr, and support.  Does not modify
    any existing function or global state.
    """
    from collections import defaultdict

    type_labels: dict[str, list[int]] = defaultdict(list)
    type_probs: dict[str, list[float]] = defaultdict(list)
    for label, prob, atype in zip(labels, probabilities, attack_types):
        type_labels[atype].append(label)
        type_probs[atype].append(prob)

    results: dict[str, dict[str, Any]] = {}
    for atype in sorted(type_labels.keys()):
        preds = binary_predictions(type_probs[atype], threshold=threshold)
        prf = precision_recall_f1(type_labels[atype], preds)
        confusion = binary_confusion(type_labels[atype], preds)
        results[atype] = {
            **confusion,
            **prf,
            "dr": prf["recall"],
            "fpr": false_positive_rate(type_labels[atype], preds),
            "support": confusion["tp"] + confusion["fn"],
        }
    return results
