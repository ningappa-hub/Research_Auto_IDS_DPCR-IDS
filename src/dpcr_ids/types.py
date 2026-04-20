"""Shared data contracts for the DPCR-IDS project."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CanSample:
    features: list[list[float]]
    label: int
    start_ts: float
    end_ts: float
    attack_type: str
    vehicle_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EthernetSample:
    features: list[list[list[float]]]
    label: int
    frame_idx: int
    protocol: str
    attack_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FusionSample:
    features: list[list[float]]
    label: int
    bucket_index: int
    can_label: int
    ethernet_label: int
    pair_type: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RuntimeAlert:
    timestamp: float
    protocol: str
    decision: str
    path: str
    p_attack_raw: float
    p_attack_calibrated: float
    latency_ms: float
    escalate_flag: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SplitManifest:
    protocol: str
    split: str
    sample_count: int
    feature_shape: list[int]
    labels: dict[str, int]
    data_path: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CalibrationArtifact:
    protocol: str
    temperature: float
    ece_before: float
    ece_after: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
