"""Shared dataset utilities."""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable
from typing import Sequence

from dpcr_ids.exceptions import DataValidationError


SPLIT_NAMES = ("train", "val", "test")


def validate_split_ratios(train_ratio: float, val_ratio: float, test_ratio: float) -> None:
    total = train_ratio + val_ratio + test_ratio
    if abs(total - 1.0) > 1e-9:
        raise DataValidationError(f"Split ratios must sum to 1.0, got {total}")


def temporal_split(items: Sequence, train_ratio: float, val_ratio: float, test_ratio: float) -> dict[str, list]:
    validate_split_ratios(train_ratio, val_ratio, test_ratio)
    total = len(items)
    train_end = int(total * train_ratio)
    val_end = int(total * (train_ratio + val_ratio))
    return {
        "train": list(items[:train_end]),
        "val": list(items[train_end:val_end]),
        "test": list(items[val_end:]),
    }



def label_distribution(labels: Iterable[int]) -> dict[str, int]:
    counts = Counter(labels)
    return {str(key): value for key, value in sorted(counts.items())}



def fit_channel_zscore(samples: Sequence[Sequence[Sequence[float]]]) -> tuple[list[float], list[float]]:
    if not samples:
        return [], []
    channel_count = len(samples[0])
    sums = [0.0] * channel_count
    sq_sums = [0.0] * channel_count
    counts = [0] * channel_count

    for sample in samples:
        for channel_index, channel in enumerate(sample):
            for value in channel:
                sums[channel_index] += value
                sq_sums[channel_index] += value * value
                counts[channel_index] += 1

    means: list[float] = []
    stds: list[float] = []
    for channel_index in range(channel_count):
        count = max(counts[channel_index], 1)
        mean = sums[channel_index] / count
        variance = max((sq_sums[channel_index] / count) - (mean * mean), 0.0)
        means.append(mean)
        stds.append(math.sqrt(variance) or 1.0)
    return means, stds



def apply_channel_zscore(sample: Sequence[Sequence[float]], means: Sequence[float], stds: Sequence[float]) -> list[list[float]]:
    normalized: list[list[float]] = []
    for channel_index, channel in enumerate(sample):
        mean = means[channel_index]
        std = stds[channel_index]
        normalized.append([(value - mean) / std for value in channel])
    return normalized
