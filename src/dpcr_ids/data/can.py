"""Car-Hacking CAN preprocessing and manifest generation."""

from __future__ import annotations

import csv
import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Iterable

from dpcr_ids.data.common import apply_channel_zscore
from dpcr_ids.data.common import fit_channel_zscore
from dpcr_ids.data.common import label_distribution
from dpcr_ids.data.common import temporal_split
from dpcr_ids.exceptions import DataValidationError
from dpcr_ids.types import CanSample
from dpcr_ids.types import SplitManifest
from dpcr_ids.utils.fs import ensure_dir
from dpcr_ids.utils.fs import write_json
from dpcr_ids.utils.fs import write_jsonl

CAN_COLUMNS = [
    "timestamp",
    "can_id",
    "dlc",
    "d0",
    "d1",
    "d2",
    "d3",
    "d4",
    "d5",
    "d6",
    "d7",
    "flag",
]


@dataclass(slots=True)
class CanFrameRecord:
    timestamp: float
    can_id: int
    dlc: int
    payload: list[int]
    flag: str
    attack_type: str


@dataclass(slots=True)
class CanFeatureRecord:
    timestamp: float
    features: list[float]
    label: int
    attack_type: str


def infer_attack_type_from_name(name: str) -> str:
    stem = Path(name).stem.lower()
    for token in ("dos", "fuzzy", "gear", "rpm"):
        if token in stem:
            return token
    return stem


def _safe_hex_to_int(value: str) -> int:
    return int(value, 16)


def read_car_hacking_csv(path: str | Path, attack_type: str | None = None) -> list[CanFrameRecord]:
    resolved = Path(path)
    if not resolved.exists():
        raise DataValidationError(f"Missing CAN dataset file: {resolved}")
    attack = attack_type or infer_attack_type_from_name(resolved.name)
    rows: list[CanFrameRecord] = []
    with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for raw_row in reader:
            if not raw_row:
                continue
            if len(raw_row) < 5:
                raise DataValidationError(f"Expected at least 5 CAN columns in {resolved}, got {len(raw_row)}")
            timestamp = float(raw_row[0])
            can_id = _safe_hex_to_int(raw_row[1])
            dlc = int(raw_row[2])
            payload_tokens = raw_row[3:-1]
            if len(payload_tokens) > 8:
                raise DataValidationError(f"Expected at most 8 payload bytes in {resolved}, got {len(payload_tokens)}")
            payload = [_safe_hex_to_int(value) for value in payload_tokens]
            payload.extend([0] * (8 - len(payload)))
            flag = raw_row[-1].strip().upper()
            rows.append(CanFrameRecord(timestamp, can_id, dlc, payload, flag, attack))
    return rows


def payload_entropy(payload: Iterable[int]) -> float:
    counts: dict[int, int] = {}
    total = 0
    for value in payload:
        counts[value] = counts.get(value, 0) + 1
        total += 1
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log(probability, 2)
    return entropy


def mean_abs_delta(current: list[int], previous: list[int] | None) -> float:
    if previous is None:
        return 0.0
    deltas = [abs(cur - prev) for cur, prev in zip(current, previous)]
    return sum(deltas) / max(len(deltas), 1)


def bitflip_ratio(current: list[int], previous: list[int] | None) -> float:
    if previous is None:
        return 0.0
    flips = 0
    total = 0
    for cur, prev in zip(current, previous):
        xor_value = cur ^ prev
        flips += bin(xor_value).count("1")
        total += 8
    return flips / total if total else 0.0


def extract_can_frame_features(records: list[CanFrameRecord]) -> list[CanFeatureRecord]:
    prev_by_id: dict[int, CanFrameRecord] = {}
    recent_timestamps: deque[float] = deque()
    feature_rows: list[CanFeatureRecord] = []

    for record in records:
        previous = prev_by_id.get(record.can_id)
        iat_same_id = 0.0 if previous is None else max(record.timestamp - previous.timestamp, 0.0)
        msg_freq_hz = 0.0 if iat_same_id <= 0 else 1.0 / iat_same_id

        recent_timestamps.append(record.timestamp)
        while recent_timestamps and (record.timestamp - recent_timestamps[0]) > 0.1:
            recent_timestamps.popleft()
        local_busload = len(recent_timestamps) / 0.1

        features = [
            record.can_id / 0x7FF,
            record.dlc / 8.0,
            *[byte / 255.0 for byte in record.payload],
            iat_same_id,
            payload_entropy(record.payload),
            mean_abs_delta(record.payload, previous.payload if previous else None) / 255.0,
            msg_freq_hz,
            local_busload,
            bitflip_ratio(record.payload, previous.payload if previous else None),
        ]
        if len(features) != 16:
            raise DataValidationError(f"Expected 16 CAN features, got {len(features)}")

        label = 1 if record.flag == "T" else 0
        attack_type = record.attack_type if label else "normal"
        feature_rows.append(CanFeatureRecord(record.timestamp, features, label, attack_type))
        prev_by_id[record.can_id] = record

    return feature_rows


def build_can_windows(
    feature_rows: list[CanFeatureRecord],
    window_size: int,
    stride: int,
    vehicle_id: str | None = None,
) -> list[CanSample]:
    samples: list[CanSample] = []
    if window_size <= 0 or stride <= 0:
        raise DataValidationError("Window size and stride must be positive")

    for start in range(0, max(len(feature_rows) - window_size + 1, 0), stride):
        window = feature_rows[start : start + window_size]
        if len(window) != window_size:
            continue
        label = 1 if any(row.label for row in window) else 0
        attack_rows = [row.attack_type for row in window if row.label]
        attack_type = attack_rows[0] if attack_rows else "normal"
        channels = [
            [row.features[channel_index] for row in window]
            for channel_index in range(len(window[0].features))
        ]
        samples.append(
            CanSample(
                features=channels,
                label=label,
                start_ts=window[0].timestamp,
                end_ts=window[-1].timestamp,
                attack_type=attack_type,
                vehicle_id=vehicle_id,
            )
        )
    return samples


def split_can_windows_attack_horizon(
    samples: list[CanSample],
    split_cfg: dict[str, float],
) -> tuple[dict[str, list[CanSample]], list[CanSample], dict[str, int]]:
    attack_indices = [index for index, sample in enumerate(samples) if sample.label]
    if not attack_indices:
        raise DataValidationError("CAN dataset does not contain any attack windows")

    usable_end = attack_indices[-1] + 1
    usable_samples = samples[:usable_end]
    tail_holdout = samples[usable_end:]
    split_samples = temporal_split(
        usable_samples,
        split_cfg["train"],
        split_cfg["val"],
        split_cfg["test"],
    )
    metadata = {
        "usable_window_count": len(usable_samples),
        "tail_holdout_count": len(tail_holdout),
        "first_attack_window": attack_indices[0],
        "last_attack_window": attack_indices[-1],
    }
    return split_samples, tail_holdout, metadata


def _write_split(
    split_name: str,
    samples: list[CanSample],
    output_dir: Path,
    window_size: int,
    normalization: dict[str, Any],
) -> SplitManifest:
    data_path = output_dir / f"{split_name}.jsonl"
    write_jsonl(data_path, [sample.to_dict() for sample in samples])
    manifest = SplitManifest(
        protocol="can",
        split=split_name,
        sample_count=len(samples),
        feature_shape=[16, window_size],
        labels=label_distribution(sample.label for sample in samples),
        data_path=str(data_path),
        metadata={"normalization": normalization},
    )
    write_json(output_dir / f"{split_name}.manifest.json", manifest.to_dict())
    return manifest


def prepare_can_dataset(
    dataset_root: str | Path,
    files: list[str],
    output_dir: str | Path,
    split_cfg: dict[str, float],
    window_size: int,
    stride: int,
) -> dict[str, Any]:
    root = Path(dataset_root)
    protocol_dir = ensure_dir(Path(output_dir) / "can")
    all_samples: dict[str, list[CanSample]] = {"train": [], "val": [], "test": []}
    tail_holdout_samples: list[CanSample] = []
    qa_files: list[dict[str, Any]] = []

    for file_name in files:
        file_path = root / file_name
        records = read_car_hacking_csv(file_path)
        feature_rows = extract_can_frame_features(records)
        windows = build_can_windows(feature_rows, window_size=window_size, stride=stride)
        split_samples, tail_holdout, horizon_metadata = split_can_windows_attack_horizon(
            windows,
            split_cfg=split_cfg,
        )
        for split_name, split_rows in split_samples.items():
            all_samples[split_name].extend(split_rows)
        tail_holdout_samples.extend(tail_holdout)
        qa_files.append(
            {
                "file": str(file_path),
                "attack_type": infer_attack_type_from_name(file_name),
                "frame_count": len(records),
                "window_count": len(windows),
                "attack_horizon": horizon_metadata,
                "split_counts": {name: len(rows) for name, rows in split_samples.items()},
            }
        )

    means, stds = fit_channel_zscore([sample.features for sample in all_samples["train"]])
    normalization = {"means": means, "stds": stds}
    for samples in all_samples.values():
        for sample in samples:
            sample.features = apply_channel_zscore(sample.features, means, stds)

    manifests = {
        split_name: _write_split(split_name, samples, protocol_dir, window_size, normalization).to_dict()
        for split_name, samples in all_samples.items()
    }
    qa_report = {
        "dataset_root": str(root),
        "files": qa_files,
        "normalization": normalization,
        "totals": {split_name: len(samples) for split_name, samples in all_samples.items()},
        "tail_holdout": {
            "sample_count": len(tail_holdout_samples),
            "label_distribution": label_distribution(sample.label for sample in tail_holdout_samples),
        },
    }
    write_json(protocol_dir / "qa_report.json", qa_report)
    return {"protocol": "can", "manifests": manifests, "qa": qa_report}
