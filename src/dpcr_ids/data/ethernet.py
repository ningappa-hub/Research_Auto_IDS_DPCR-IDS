"""Automotive Ethernet preprocessing and dataset manifests."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Iterable

from dpcr_ids.data.common import label_distribution
from dpcr_ids.data.common import temporal_split
from dpcr_ids.exceptions import DataValidationError
from dpcr_ids.types import EthernetSample
from dpcr_ids.types import SplitManifest
from dpcr_ids.utils.deps import require_dependency
from dpcr_ids.utils.fs import ensure_dir
from dpcr_ids.utils.fs import write_json
from dpcr_ids.utils.fs import write_jsonl

L2_HEADER_BYTES = 14
TOW_LIKE_LABEL_MAP: dict[str, tuple[int, str, str]] = {
    "normal": (0, "ethernet", "normal"),
    "avtp_bg": (0, "avtp", "avtp_background"),
    "gptp_bg": (0, "gptp", "gptp_background"),
    "c_d": (1, "udp", "can_dos_tunneled"),
    "c_r": (1, "udp", "can_replay_tunneled"),
    "f_i": (1, "avtp", "frame_injection"),
    "p_i": (1, "gptp", "ptp_injection"),
    "m_f": (1, "ethernet", "mac_flooding"),
}


@dataclass(slots=True)
class TowLabelRecord:
    frame_idx: int
    label: int
    protocol: str
    attack_type: str
    raw_label: str = ""


def strip_l2_header(frame_bytes: bytes) -> bytes:
    return frame_bytes[L2_HEADER_BYTES:] if len(frame_bytes) > L2_HEADER_BYTES else b""


def _normalize_label_record(
    label_value: str,
    protocol_value: str | None = None,
    attack_type_value: str | None = None,
) -> tuple[int, str, str, str]:
    normalized = label_value.strip().lower()
    if normalized in {"1", "attack", "attacked", "malicious", "true", "t", "abnormal"}:
        return 1, (protocol_value or "ethernet"), (attack_type_value or "attack"), normalized
    if normalized in {"0", "normal", "benign", "false", "r"}:
        return 0, (protocol_value or "ethernet"), (attack_type_value or "normal"), normalized
    if normalized in TOW_LIKE_LABEL_MAP:
        label, mapped_protocol, mapped_attack = TOW_LIKE_LABEL_MAP[normalized]
        return label, (protocol_value or mapped_protocol), (attack_type_value or mapped_attack), normalized
    raise DataValidationError(f"Unsupported Ethernet label value: {label_value}")


def _parse_frame_index(token: str, row_index: int) -> int:
    try:
        value = int(token)
    except (TypeError, ValueError):
        return row_index
    return value - 1 if value > 0 else value


def _protocol_attack_from_family(family_value: str) -> tuple[str, str]:
    normalized = family_value.strip().lower()
    if normalized in TOW_LIKE_LABEL_MAP:
        _, protocol, attack_type = TOW_LIKE_LABEL_MAP[normalized]
        return protocol, attack_type
    if normalized in {"", "normal", "benign"}:
        return "ethernet", "normal"
    return "ethernet", family_value.strip() or "attack"


def _parse_official_tow_row(row: list[str], row_index: int) -> TowLabelRecord | None:
    if len(row) < 3:
        return None
    status = row[1].strip().lower()
    if status not in {"normal", "abnormal"}:
        return None

    frame_idx = _parse_frame_index(row[0], row_index)
    family = row[2].strip()
    if status == "normal":
        return TowLabelRecord(
            frame_idx=frame_idx,
            label=0,
            protocol="ethernet",
            attack_type="normal",
            raw_label="normal",
        )

    protocol, attack_type = _protocol_attack_from_family(family)
    return TowLabelRecord(
        frame_idx=frame_idx,
        label=1,
        protocol=protocol,
        attack_type=attack_type,
        raw_label=family.lower(),
    )


def read_label_csv(path: str | Path) -> list[TowLabelRecord]:
    resolved = Path(path)
    if not resolved.exists():
        raise DataValidationError(f"Missing Ethernet label CSV: {resolved}")

    labels: list[TowLabelRecord] = []
    with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        has_header = csv.Sniffer().has_header(sample) if sample.strip() else False
        if has_header:
            first_line = sample.splitlines()[0] if sample.splitlines() else ""
            first_fields = [field.strip().lower() for field in next(csv.reader([first_line]), [])]
            known_header_fields = {"frame_idx", "index", "frame", "label", "class", "protocol", "attack_type", "attack"}
            has_header = any(field in known_header_fields for field in first_fields)
        if has_header:
            reader = csv.DictReader(handle)
            row_index = 0
            for row in reader:
                if not row:
                    continue
                label_value = str(row.get("label") or row.get("class") or "0")
                frame_token = row.get("frame_idx") or row.get("index") or row.get("frame")
                frame_idx = row_index if frame_token in (None, "") else int(frame_token)
                label, protocol, attack_type, raw_label = _normalize_label_record(
                    label_value,
                    protocol_value=(row.get("protocol") or None),
                    attack_type_value=(row.get("attack_type") or row.get("attack") or None),
                )
                labels.append(
                    TowLabelRecord(
                        frame_idx=frame_idx,
                        label=label,
                        protocol=protocol,
                        attack_type=attack_type,
                        raw_label=raw_label,
                    )
                )
                row_index += 1
        else:
            reader = csv.reader(handle)
            row_index = 0
            for row in reader:
                if not row:
                    continue
                official_record = _parse_official_tow_row(row, row_index)
                if official_record is not None:
                    labels.append(official_record)
                    row_index += 1
                    continue

                frame_idx = _parse_frame_index(row[0], row_index) if len(row) > 1 else row_index
                label_value = row[1] if len(row) > 1 else row[0]
                protocol_value = row[2] if len(row) > 2 else None
                attack_value = row[3] if len(row) > 3 else None
                label, protocol, attack_type, raw_label = _normalize_label_record(
                    label_value,
                    protocol_value=protocol_value,
                    attack_type_value=attack_value,
                )
                labels.append(
                    TowLabelRecord(
                        frame_idx=frame_idx,
                        label=label,
                        protocol=protocol,
                        attack_type=attack_type,
                        raw_label=raw_label,
                    )
                )
                row_index += 1
    return labels


def bytes_to_byte_image(
    payload: bytes,
    prev_payload: bytes | None = None,
    iat_ms: float = 0.0,
    payload_bytes: int = 1024,
    frame_height: int = 32,
    frame_width: int = 32,
) -> list[list[list[float]]]:
    padded = list(payload[:payload_bytes])
    padded.extend([0] * max(payload_bytes - len(padded), 0))

    previous = list((prev_payload or b"")[:payload_bytes])
    previous.extend([0] * max(payload_bytes - len(previous), 0))

    if frame_height * frame_width != payload_bytes:
        raise DataValidationError("Frame dimensions must multiply to payload_bytes")

    normalized_iat = min(max(iat_ms / 100.0, 0.0), 1.0)

    value_channel: list[list[float]] = []
    delta_channel: list[list[float]] = []
    position_channel: list[list[float]] = []
    temporal_channel: list[list[float]] = []
    for row_index in range(frame_height):
        value_row: list[float] = []
        delta_row: list[float] = []
        position_row: list[float] = []
        temporal_row: list[float] = []
        for col_index in range(frame_width):
            offset = row_index * frame_width + col_index
            current_value = padded[offset]
            previous_value = previous[offset]
            value_row.append(current_value / 255.0)
            delta_row.append(max(-1.0, min(1.0, (current_value - previous_value) / 255.0)))
            position_row.append(offset / payload_bytes)
            temporal_row.append(normalized_iat)
        value_channel.append(value_row)
        delta_channel.append(delta_row)
        position_channel.append(position_row)
        temporal_channel.append(temporal_row)
    return [value_channel, delta_channel, position_channel, temporal_channel]


def paired_smoke_adapter(root: str | Path) -> list[dict[str, str]]:
    resolved = Path(root)
    if not resolved.exists():
        return []
    pairs: list[dict[str, str]] = []
    originals = sorted(resolved.glob("*_original.pcap"))
    for original in originals:
        injected = original.with_name(original.name.replace("_original.pcap", "_injected.pcap"))
        if injected.exists():
            pairs.append({"scenario": original.stem.replace("_original", ""), "original": str(original), "injected": str(injected)})
    return pairs


def iter_pcap_payloads(path: str | Path) -> list[dict[str, Any]]:
    scapy_all = require_dependency("scapy.all")
    packets = scapy_all.PcapReader(str(path))
    frames: list[dict[str, Any]] = []
    try:
        for frame_idx, packet in enumerate(packets):
            raw_frame = bytes(packet)
            payload = strip_l2_header(raw_frame)
            protocol = getattr(packet.lastlayer(), "name", "ethernet").lower()
            timestamp = float(packet.time)
            frames.append({"frame_idx": frame_idx, "payload": payload, "protocol": protocol, "timestamp": timestamp})
    finally:
        packets.close()
    return frames


def build_ethernet_samples(
    frames: Iterable[dict[str, Any]],
    labels: list[TowLabelRecord],
    payload_bytes: int,
    frame_height: int,
    frame_width: int,
) -> list[EthernetSample]:
    frame_list = list(frames)
    if len(frame_list) != len(labels):
        raise DataValidationError(
            f"Frame count mismatch between PCAP and labels: {len(frame_list)} != {len(labels)}"
        )

    prev_by_protocol: dict[str, bytes] = {}
    prev_ts_by_protocol: dict[str, float] = {}
    samples: list[EthernetSample] = []
    for frame, label in zip(frame_list, labels):
        previous_payload = prev_by_protocol.get(label.protocol)
        
        current_ts = frame.get("timestamp", 0.0)
        previous_ts = prev_ts_by_protocol.get(label.protocol, current_ts)
        iat_ms = (current_ts - previous_ts) * 1000.0
        
        features = bytes_to_byte_image(
            frame["payload"],
            prev_payload=previous_payload,
            iat_ms=iat_ms,
            payload_bytes=payload_bytes,
            frame_height=frame_height,
            frame_width=frame_width,
        )
        samples.append(
            EthernetSample(
                features=features,
                label=label.label,
                frame_idx=label.frame_idx,
                protocol=label.protocol,
                attack_type=label.attack_type,
            )
        )
        prev_by_protocol[label.protocol] = frame["payload"]
        prev_ts_by_protocol[label.protocol] = current_ts
    return samples


def _is_macosx_sidecar(path: Path) -> bool:
    return any(part == "__MACOSX" for part in path.parts) or path.name.startswith("._")


def infer_dataset_variant(label_file: str | Path) -> str:
    resolved = Path(label_file)
    if resolved.stem.startswith("tow_like"):
        return "surrogate_tow_like"
    if resolved.name.lower() in {"y_train.csv", "y_test.csv"}:
        return "official_tow_ids"
    return "official_like"


def _select_label_files(root: Path, label_csv_glob: str) -> list[Path]:
    label_files = [path for path in sorted(root.rglob(label_csv_glob)) if not _is_macosx_sidecar(path)]
    official_files = [path for path in label_files if infer_dataset_variant(path) == "official_tow_ids"]
    return official_files or label_files


def _first_existing_match(root: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = [path for path in sorted(root.rglob(pattern)) if not _is_macosx_sidecar(path)]
        if matches:
            return matches[0]
    return None


def resolve_pcap_for_label_csv(label_file: str | Path, dataset_root: str | Path) -> Path | None:
    resolved = Path(label_file)
    direct = resolved.with_suffix(".pcap")
    if direct.exists():
        return direct

    root = Path(dataset_root)
    name = resolved.name.lower()
    if name == "y_train.csv":
        match = _first_existing_match(root, ["*training*.pcap", "*train*.pcap"])
        if match is not None:
            return match
    if name == "y_test.csv":
        match = _first_existing_match(root, ["*test*.pcap"])
        if match is not None:
            return match

    generated_candidate = root / "data" / "generated" / f"{resolved.stem}.pcap"
    if generated_candidate.exists():
        return generated_candidate

    matches = [path for path in sorted(root.rglob(f"{resolved.stem}.pcap")) if not _is_macosx_sidecar(path)]
    return matches[0] if matches else None


def _write_split(
    split_name: str,
    samples: list[EthernetSample],
    output_dir: Path,
    feature_shape: list[int],
    metadata: dict[str, Any],
) -> SplitManifest:
    data_path = output_dir / f"{split_name}.jsonl"
    write_jsonl(data_path, [sample.to_dict() for sample in samples])
    manifest = SplitManifest(
        protocol="ethernet",
        split=split_name,
        sample_count=len(samples),
        feature_shape=feature_shape,
        labels=label_distribution(sample.label for sample in samples),
        data_path=str(data_path),
        metadata=metadata,
    )
    write_json(output_dir / f"{split_name}.manifest.json", manifest.to_dict())
    return manifest


def _write_streamed_manifest(
    split_name: str,
    data_path: Path,
    output_dir: Path,
    feature_shape: list[int],
    labels: Counter[int],
    sample_count: int,
    metadata: dict[str, Any],
) -> SplitManifest:
    manifest = SplitManifest(
        protocol="ethernet",
        split=split_name,
        sample_count=sample_count,
        feature_shape=feature_shape,
        labels={str(key): value for key, value in sorted(labels.items())},
        data_path=str(data_path),
        metadata=metadata,
    )
    write_json(output_dir / f"{split_name}.manifest.json", manifest.to_dict())
    return manifest


def _split_for_official_tow(label_file: Path, sample_index: int, total_labels: int, split_cfg: dict[str, float]) -> str:
    name = label_file.name.lower()
    if name == "y_test.csv":
        return "test"
    if name == "y_train.csv":
        train_val_total = float(split_cfg["train"]) + float(split_cfg["val"])
        train_ratio = float(split_cfg["train"]) / train_val_total
        train_end = int(total_labels * train_ratio)
        return "train" if sample_index < train_end else "val"
    train_end = int(total_labels * float(split_cfg["train"]))
    val_end = int(total_labels * (float(split_cfg["train"]) + float(split_cfg["val"])))
    if sample_index < train_end:
        return "train"
    if sample_index < val_end:
        return "val"
    return "test"


def _stream_official_tow_ids_dataset(
    label_files: list[Path],
    root: Path,
    protocol_dir: Path,
    qa_report: dict[str, Any],
    split_cfg: dict[str, float],
    payload_bytes: int,
    frame_height: int,
    frame_width: int,
) -> dict[str, Any]:
    scapy_all = require_dependency("scapy.all")
    feature_shape = [4, frame_height, frame_width]
    manifest_metadata = {
        "source_variants": ["official_tow_ids"],
        "surrogate_only": False,
        "intended_use": "primary_official_tow_ids",
        "storage_mode": "streamed_jsonl",
    }
    split_paths = {split_name: protocol_dir / f"{split_name}.jsonl" for split_name in ("train", "val", "test")}
    split_counts: dict[str, int] = {split_name: 0 for split_name in split_paths}
    split_label_counts: dict[str, Counter[int]] = {split_name: Counter() for split_name in split_paths}
    raw_labels: Counter[str] = Counter()
    label_reports: list[dict[str, Any]] = []

    handles = {split_name: path.open("w", encoding="utf-8") for split_name, path in split_paths.items()}
    try:
        for label_file in label_files:
            pcap_file = resolve_pcap_for_label_csv(label_file, root)
            if pcap_file is None or not pcap_file.exists():
                continue
            labels = read_label_csv(label_file)
            file_split_counts: Counter[str] = Counter()
            file_raw_labels = Counter(label.raw_label for label in labels)
            raw_labels.update(file_raw_labels)
            prev_by_protocol: dict[str, bytes] = {}
            prev_ts_by_protocol: dict[str, float] = {}
            packet_count = 0

            packets = scapy_all.PcapReader(str(pcap_file))
            try:
                packet_iterator = iter(packets)
                for sample_index, label in enumerate(labels):
                    try:
                        packet = next(packet_iterator)
                    except StopIteration as exc:
                        raise DataValidationError(
                            f"Frame count mismatch between PCAP and labels for {label_file}: fewer packets than {len(labels)} labels"
                        ) from exc
                    raw_frame = bytes(packet)
                    payload = strip_l2_header(raw_frame)
                    previous_payload = prev_by_protocol.get(label.protocol)
                    
                    current_ts = float(packet.time)
                    previous_ts = prev_ts_by_protocol.get(label.protocol, current_ts)
                    iat_ms = (current_ts - previous_ts) * 1000.0
                    
                    features = bytes_to_byte_image(
                        payload,
                        prev_payload=previous_payload,
                        iat_ms=iat_ms,
                        payload_bytes=payload_bytes,
                        frame_height=frame_height,
                        frame_width=frame_width,
                    )
                    sample = EthernetSample(
                        features=features,
                        label=label.label,
                        frame_idx=label.frame_idx,
                        protocol=label.protocol,
                        attack_type=label.attack_type,
                    )
                    split_name = _split_for_official_tow(label_file, sample_index, len(labels), split_cfg)
                    handles[split_name].write(json.dumps(sample.to_dict()))
                    handles[split_name].write("\n")
                    split_counts[split_name] += 1
                    split_label_counts[split_name].update([label.label])
                    file_split_counts.update([split_name])
                    prev_by_protocol[label.protocol] = payload
                    prev_ts_by_protocol[label.protocol] = current_ts
                    packet_count += 1
                    if packet_count % 100000 == 0:
                        print(
                            f"ethernet_prepare official_tow file={label_file.name} processed={packet_count}/{len(labels)}"
                        )
                sentinel = object()
                if next(packet_iterator, sentinel) is not sentinel:
                    raise DataValidationError(
                        f"Frame count mismatch between PCAP and labels for {label_file}: more packets than {len(labels)} labels"
                    )
            finally:
                packets.close()

            label_reports.append(
                {
                    "pcap": str(pcap_file),
                    "labels": str(label_file),
                    "sample_count": len(labels),
                    "split_counts": dict(sorted(file_split_counts.items())),
                    "dataset_variant": "official_tow_ids",
                    "surrogate_only": False,
                    "raw_label_distribution": dict(sorted(file_raw_labels.items())),
                    "storage_mode": "streamed_jsonl",
                }
            )
    finally:
        for handle in handles.values():
            handle.close()

    if not any(split_counts.values()):
        qa_report["dataset_available"] = False
        qa_report["reason"] = "No matching official TOW-IDS PCAP/label pairs found"
        write_json(protocol_dir / "qa_report.json", qa_report)
        return {"protocol": "ethernet", "manifests": {}, "qa": qa_report}

    manifests = {
        split_name: _write_streamed_manifest(
            split_name,
            split_paths[split_name],
            protocol_dir,
            feature_shape,
            split_label_counts[split_name],
            split_counts[split_name],
            manifest_metadata,
        ).to_dict()
        for split_name in split_paths
    }
    qa_report.update(
        {
            "dataset_available": True,
            "label_reports": label_reports,
            "totals": split_counts,
            "source_variants": {"official_tow_ids": len(label_reports)},
            "raw_label_distribution": dict(sorted(raw_labels.items())),
            "surrogate_only": False,
            "intended_use": "primary_official_tow_ids",
            "storage_mode": "streamed_jsonl",
        }
    )
    write_json(protocol_dir / "qa_report.json", qa_report)
    return {"protocol": "ethernet", "manifests": manifests, "qa": qa_report}


def prepare_ethernet_dataset(
    primary_dataset_root: str | Path,
    smoke_dataset_root: str | Path,
    output_dir: str | Path,
    split_cfg: dict[str, float],
    payload_bytes: int,
    frame_height: int,
    frame_width: int,
    label_csv_glob: str = "*.csv",
) -> dict[str, Any]:
    protocol_dir = ensure_dir(Path(output_dir) / "ethernet")
    smoke_pairs = paired_smoke_adapter(smoke_dataset_root)
    qa_report: dict[str, Any] = {"primary_dataset_root": str(primary_dataset_root), "smoke_pairs": smoke_pairs}

    root = Path(primary_dataset_root)
    if not root.exists():
        qa_report["dataset_available"] = False
        write_json(protocol_dir / "qa_report.json", qa_report)
        return {"protocol": "ethernet", "manifests": {}, "qa": qa_report}

    label_files = _select_label_files(root, label_csv_glob)
    if not label_files:
        qa_report["dataset_available"] = False
        qa_report["reason"] = "No label CSVs found"
        write_json(protocol_dir / "qa_report.json", qa_report)
        return {"protocol": "ethernet", "manifests": {}, "qa": qa_report}

    if all(infer_dataset_variant(label_file) == "official_tow_ids" for label_file in label_files):
        return _stream_official_tow_ids_dataset(
            label_files=label_files,
            root=root,
            protocol_dir=protocol_dir,
            qa_report=qa_report,
            split_cfg=split_cfg,
            payload_bytes=payload_bytes,
            frame_height=frame_height,
            frame_width=frame_width,
        )

    all_samples: dict[str, list[EthernetSample]] = {"train": [], "val": [], "test": []}
    label_reports: list[dict[str, Any]] = []
    variants: Counter[str] = Counter()
    raw_labels: Counter[str] = Counter()
    surrogate_only = True

    for label_file in label_files:
        pcap_file = resolve_pcap_for_label_csv(label_file, root)
        if pcap_file is None or not pcap_file.exists():
            continue
        labels = read_label_csv(label_file)
        frames = iter_pcap_payloads(pcap_file)
        samples = build_ethernet_samples(frames, labels, payload_bytes, frame_height, frame_width)
        variant = infer_dataset_variant(label_file)
        if variant == "official_tow_ids" and label_file.name.lower() == "y_train.csv":
            train_val_total = float(split_cfg["train"]) + float(split_cfg["val"])
            split_samples = temporal_split(
                samples,
                float(split_cfg["train"]) / train_val_total,
                float(split_cfg["val"]) / train_val_total,
                0.0,
            )
        elif variant == "official_tow_ids" and label_file.name.lower() == "y_test.csv":
            split_samples = {"train": [], "val": [], "test": samples}
        else:
            split_samples = temporal_split(samples, split_cfg["train"], split_cfg["val"], split_cfg["test"])
        for split_name, rows in split_samples.items():
            all_samples[split_name].extend(rows)

        variants[variant] += 1
        if variant != "surrogate_tow_like":
            surrogate_only = False
        raw_labels.update(label.raw_label for label in labels)
        label_reports.append(
            {
                "pcap": str(pcap_file),
                "labels": str(label_file),
                "sample_count": len(samples),
                "split_counts": {name: len(rows) for name, rows in split_samples.items()},
                "dataset_variant": variant,
                "surrogate_only": variant == "surrogate_tow_like",
                "raw_label_distribution": dict(sorted(Counter(label.raw_label for label in labels).items())),
            }
        )

    if not any(all_samples.values()):
        qa_report["dataset_available"] = False
        qa_report["reason"] = "No matching PCAP/label pairs found"
        write_json(protocol_dir / "qa_report.json", qa_report)
        return {"protocol": "ethernet", "manifests": {}, "qa": qa_report}

    manifest_metadata = {
        "source_variants": sorted(variants.keys()),
        "surrogate_only": surrogate_only,
        "intended_use": "surrogate_testing_only" if surrogate_only else "primary_or_mixed",
    }
    manifests = {
        split_name: _write_split(
            split_name,
            rows,
            protocol_dir,
            [4, frame_height, frame_width],
            metadata=manifest_metadata,
        ).to_dict()
        for split_name, rows in all_samples.items()
    }
    qa_report.update(
        {
            "dataset_available": True,
            "label_reports": label_reports,
            "totals": {split_name: len(rows) for split_name, rows in all_samples.items()},
            "source_variants": dict(sorted(variants.items())),
            "raw_label_distribution": dict(sorted(raw_labels.items())),
            "surrogate_only": surrogate_only,
            "intended_use": "surrogate_testing_only" if surrogate_only else "primary_or_mixed",
        }
    )
    write_json(protocol_dir / "qa_report.json", qa_report)
    return {"protocol": "ethernet", "manifests": manifests, "qa": qa_report}
