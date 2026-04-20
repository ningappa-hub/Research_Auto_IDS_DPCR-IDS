"""Late-fusion dataset and model helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Iterable

from dpcr_ids.data.common import label_distribution
from dpcr_ids.models import TinyLateFusionMetaModel
from dpcr_ids.models import stack_expert_outputs
from dpcr_ids.types import FusionSample
from dpcr_ids.types import SplitManifest
from dpcr_ids.utils.deps import require_dependency
from dpcr_ids.utils.fs import read_jsonl
from dpcr_ids.utils.fs import write_json
from dpcr_ids.utils.fs import write_jsonl

FUSION_PROTOCOL = "fusion"
FUSION_EXPERT_ORDER = ("can", "ethernet")
PAIR_TYPE_ORDER = ("AA", "AN", "NA", "NN")
PAIR_TYPE_LABELS = {
    "AA": (1, 1),
    "AN": (1, 0),
    "NA": (0, 1),
    "NN": (0, 0),
}
FUSION_PAIRING_METHOD = "coverage_aware_pseudo_time"
FUSION_DEFAULTS = {
    "enabled": False,
    "expert_order": ["can", "ethernet"],
    "expert_dim": 129,
    "hidden_dim": 8,
    "fusion_dim": 16,
    "bucket_ms": 250,
    "use_raw_logits": True,
    "pseudo_time_step": 0.01,
}

PreparedDatasetFn = Callable[[dict[str, Any], str, str], Any]
LoadExactModelFn = Callable[[dict[str, Any], str, str], tuple[Any, Path]]
PredictDatasetFn = Callable[[Any, Any, str, int, Any], tuple[list[int], list[float], list[float], list[list[float]]]]
ResolveDeviceFn = Callable[[Any], Any]
CloseDatasetFn = Callable[[Any], None]


def fusion_config(config: dict[str, Any]) -> dict[str, Any]:
    payload = dict(FUSION_DEFAULTS)
    payload.update(config.get("fusion", {}))
    payload["expert_order"] = [str(item) for item in payload.get("expert_order", FUSION_EXPERT_ORDER)]
    if tuple(payload["expert_order"]) != FUSION_EXPERT_ORDER:
        raise ValueError("Fusion expert order must be the fixed list ['can', 'ethernet']")
    if int(payload["expert_dim"]) != 129:
        raise ValueError("Fusion expert_dim must be 129 (1 raw logit + 128 embedding)")
    if int(payload["hidden_dim"]) <= 0 or int(payload["fusion_dim"]) <= 0:
        raise ValueError("Fusion hidden_dim and fusion_dim must be positive")
    if int(payload["bucket_ms"]) <= 0:
        raise ValueError("Fusion bucket_ms must be positive")
    if float(payload["pseudo_time_step"]) <= 0:
        raise ValueError("Fusion pseudo_time_step must be positive")
    return payload


def require_fusion_enabled(config: dict[str, Any]) -> dict[str, Any]:
    payload = fusion_config(config)
    if not bool(payload.get("enabled", False)):
        raise ValueError("Fusion is disabled in config. Set fusion.enabled=true before using protocol 'fusion'.")
    return payload


def build_fusion_model(config: dict[str, Any]) -> TinyLateFusionMetaModel:
    payload = require_fusion_enabled(config)
    return TinyLateFusionMetaModel(
        num_experts=2,
        expert_dim=int(payload["expert_dim"]),
        hidden_dim=int(payload["hidden_dim"]),
        fusion_dim=int(payload["fusion_dim"]),
    )


def _prepared_split_path(config: dict[str, Any], split: str) -> Path:
    return Path(config["artifacts_dir"]) / "prepared" / FUSION_PROTOCOL / f"{split}.jsonl"


def _prepared_manifest_path(config: dict[str, Any], split: str) -> Path:
    return Path(config["artifacts_dir"]) / "prepared" / FUSION_PROTOCOL / f"{split}.manifest.json"


def _prepared_report_path(config: dict[str, Any]) -> Path:
    return Path(config["artifacts_dir"]) / "prepared" / FUSION_PROTOCOL / "qa_report.json"


def fusion_samples_per_bucket(bucket_ms: int, pseudo_time_step: float) -> int:
    return max(int(round(bucket_ms / (pseudo_time_step * 1000.0))), 1)


def _mean_embedding(embeddings: list[list[float]]) -> list[float]:
    if not embeddings:
        return []
    width = len(embeddings[0])
    return [sum(embedding[index] for embedding in embeddings) / len(embeddings) for index in range(width)]


def _bucket_protocol_outputs(
    protocol: str,
    labels: list[int],
    scores: list[float],
    embeddings: list[list[float]],
    bucket_ms: int,
    pseudo_time_step: float,
) -> list[dict[str, Any]]:
    if not labels:
        raise ValueError(f"No prepared samples found for protocol {protocol}")

    samples_per_bucket = fusion_samples_per_bucket(bucket_ms, pseudo_time_step)
    buckets: list[dict[str, Any]] = []
    for bucket_index, start in enumerate(range(0, len(labels), samples_per_bucket)):
        end = min(start + samples_per_bucket, len(labels))
        bucket_labels = labels[start:end]
        bucket_scores = scores[start:end]
        bucket_embeddings = embeddings[start:end]
        buckets.append(
            {
                "protocol": protocol,
                "bucket_index": bucket_index,
                "label": 1 if any(bucket_labels) else 0,
                "mean_score": sum(bucket_scores) / len(bucket_scores),
                "mean_embedding": _mean_embedding(bucket_embeddings),
                "member_count": len(bucket_labels),
                "sequence_start": start,
                "sequence_end": end - 1,
                "pseudo_time_start": start * pseudo_time_step,
                "pseudo_time_end": (end - 1) * pseudo_time_step,
            }
        )
    return buckets


def pair_type_from_labels(can_label: int, ethernet_label: int) -> str:
    for pair_type, labels in PAIR_TYPE_LABELS.items():
        if labels == (int(can_label), int(ethernet_label)):
            return pair_type
    raise ValueError(f"Unsupported fusion pair labels: can={can_label}, ethernet={ethernet_label}")


def _empty_pair_type_counts() -> dict[str, int]:
    return {pair_type: 0 for pair_type in PAIR_TYPE_ORDER}


def _label_counts(buckets: list[dict[str, Any]]) -> dict[int, int]:
    attack_count = sum(int(bucket["label"]) for bucket in buckets)
    return {1: attack_count, 0: len(buckets) - attack_count}


def _select_evenly_spaced_indices(length: int, count: int) -> list[int]:
    if count < 0 or count > length:
        raise ValueError(f"Cannot select {count} items from a pool of size {length}")
    if count == 0:
        return []
    if count == length:
        return list(range(length))
    return [min(int(((index + 0.5) * length) / count), length - 1) for index in range(count)]


def _select_evenly_spaced(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    return [items[index] for index in _select_evenly_spaced_indices(len(items), count)]


def _partition_selected_pool(
    selected_pool: list[dict[str, Any]],
    allocations: list[tuple[str, int]],
) -> dict[str, list[dict[str, Any]]]:
    allocation_map = {name: count for name, count in allocations}
    if sum(allocation_map.values()) != len(selected_pool):
        raise ValueError("Selected pool size does not match requested partition allocations")

    partitions: dict[str, list[dict[str, Any]]] = {name: [] for name, _ in allocations}
    remaining_positions = list(range(len(selected_pool)))
    nonzero_allocations = [(name, count) for name, count in allocations if count > 0]
    for allocation_index, (name, count) in enumerate(nonzero_allocations):
        if allocation_index == len(nonzero_allocations) - 1:
            chosen_positions = list(range(len(remaining_positions)))
        else:
            chosen_positions = _select_evenly_spaced_indices(len(remaining_positions), count)
        chosen_set = set(chosen_positions)
        chosen_pool_indices = [remaining_positions[position] for position in chosen_positions]
        partitions[name] = [selected_pool[position] for position in chosen_pool_indices]
        remaining_positions = [
            original_position
            for position, original_position in enumerate(remaining_positions)
            if position not in chosen_set
        ]
    return partitions


def _allocate_pair_type_counts(
    can_buckets: list[dict[str, Any]],
    eth_buckets: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, int]]:
    can_counts = _label_counts(can_buckets)
    eth_counts = _label_counts(eth_buckets)
    total_can = len(can_buckets)
    total_eth = len(eth_buckets)
    paired_total = min(total_can, total_eth)
    if paired_total <= 0:
        raise ValueError("Fusion pairing requires at least one bucket from each protocol")

    ideal_counts = {
        pair_type: paired_total
        * (can_counts[PAIR_TYPE_LABELS[pair_type][0]] / max(total_can, 1))
        * (eth_counts[PAIR_TYPE_LABELS[pair_type][1]] / max(total_eth, 1))
        for pair_type in PAIR_TYPE_ORDER
    }
    pair_counts = _empty_pair_type_counts()
    can_remaining = dict(can_counts)
    eth_remaining = dict(eth_counts)
    feasible = [
        pair_type
        for pair_type in PAIR_TYPE_ORDER
        if can_counts[PAIR_TYPE_LABELS[pair_type][0]] > 0 and eth_counts[PAIR_TYPE_LABELS[pair_type][1]] > 0
    ]

    def _label_coverage(pair_type: str) -> set[str]:
        can_label, eth_label = PAIR_TYPE_LABELS[pair_type]
        return {
            "can_attack" if can_label == 1 else "can_normal",
            "ethernet_attack" if eth_label == 1 else "ethernet_normal",
        }

    assigned = 0
    uncovered = {
        label_name
        for label_name, count in {
            "can_attack": can_counts[1],
            "can_normal": can_counts[0],
            "ethernet_attack": eth_counts[1],
            "ethernet_normal": eth_counts[0],
        }.items()
        if count > 0
    }
    while assigned < paired_total and uncovered:
        candidates: list[tuple[int, int, float, int, str]] = []
        for pair_type in feasible:
            can_label, eth_label = PAIR_TYPE_LABELS[pair_type]
            if can_remaining[can_label] <= 0 or eth_remaining[eth_label] <= 0:
                continue
            coverage = _label_coverage(pair_type)
            newly_covered = len(coverage & uncovered)
            if newly_covered <= 0:
                continue
            attack_coverage = sum(1 for label_name in coverage if "attack" in label_name and label_name in uncovered)
            candidates.append(
                (
                    newly_covered,
                    attack_coverage,
                    ideal_counts[pair_type],
                    -PAIR_TYPE_ORDER.index(pair_type),
                    pair_type,
                )
            )
        if not candidates:
            break
        _, _, _, _, chosen = max(candidates)
        can_label, eth_label = PAIR_TYPE_LABELS[chosen]
        pair_counts[chosen] += 1
        can_remaining[can_label] -= 1
        eth_remaining[eth_label] -= 1
        uncovered -= _label_coverage(chosen)
        assigned += 1

    reserve_order = sorted(feasible, key=lambda pair_type: (-ideal_counts[pair_type], PAIR_TYPE_ORDER.index(pair_type)))
    for pair_type in reserve_order:
        if assigned >= paired_total:
            break
        if pair_counts[pair_type] > 0:
            continue
        can_label, eth_label = PAIR_TYPE_LABELS[pair_type]
        if can_remaining[can_label] <= 0 or eth_remaining[eth_label] <= 0:
            continue
        pair_counts[pair_type] += 1
        can_remaining[can_label] -= 1
        eth_remaining[eth_label] -= 1
        assigned += 1

    while assigned < paired_total:
        candidates: list[tuple[float, float, int, str]] = []
        for pair_type in feasible:
            can_label, eth_label = PAIR_TYPE_LABELS[pair_type]
            if can_remaining[can_label] <= 0 or eth_remaining[eth_label] <= 0:
                continue
            deficit = ideal_counts[pair_type] - pair_counts[pair_type]
            candidates.append((deficit, ideal_counts[pair_type], -PAIR_TYPE_ORDER.index(pair_type), pair_type))
        if not candidates:
            break
        _, _, _, chosen = max(candidates)
        can_label, eth_label = PAIR_TYPE_LABELS[chosen]
        pair_counts[chosen] += 1
        can_remaining[can_label] -= 1
        eth_remaining[eth_label] -= 1
        assigned += 1

    if assigned != paired_total:
        raise ValueError("Coverage-aware pairing failed to allocate the requested number of paired buckets")
    return pair_counts, {
        "can_bucket_count": total_can,
        "can_attack_bucket_count": can_counts[1],
        "can_normal_bucket_count": can_counts[0],
        "ethernet_bucket_count": total_eth,
        "ethernet_attack_bucket_count": eth_counts[1],
        "ethernet_normal_bucket_count": eth_counts[0],
        "paired_bucket_count": paired_total,
        "truncated_can_buckets": max(total_can - paired_total, 0),
        "truncated_ethernet_buckets": max(total_eth - paired_total, 0),
    }


def fusion_rows_summary(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    row_list = list(rows)
    pair_type_counts = _empty_pair_type_counts()
    for row in row_list:
        pair_type = str(
            row.get("pair_type")
            or row.get("metadata", {}).get("pair_type")
            or pair_type_from_labels(int(row["can_label"]), int(row["ethernet_label"]))
        )
        pair_type_counts[pair_type] += 1
    paired_can_attack = sum(int(row["can_label"]) for row in row_list)
    paired_ethernet_attack = sum(int(row["ethernet_label"]) for row in row_list)
    return {
        "paired_bucket_count": len(row_list),
        "paired_can_attack_bucket_count": paired_can_attack,
        "paired_can_normal_bucket_count": len(row_list) - paired_can_attack,
        "paired_ethernet_attack_bucket_count": paired_ethernet_attack,
        "paired_ethernet_normal_bucket_count": len(row_list) - paired_ethernet_attack,
        "joint_attack_bucket_count": pair_type_counts["AA"],
        "pair_type_counts": pair_type_counts,
        "pairing_method": FUSION_PAIRING_METHOD,
        "surrogate_pairing": FUSION_PAIRING_METHOD,
        "expert_order": list(FUSION_EXPERT_ORDER),
    }


def _write_fusion_split(
    config: dict[str, Any],
    split_name: str,
    samples: list[FusionSample],
    metadata: dict[str, Any],
) -> SplitManifest:
    protocol_dir = Path(config["artifacts_dir"]) / "prepared" / FUSION_PROTOCOL
    protocol_dir.mkdir(parents=True, exist_ok=True)
    data_path = _prepared_split_path(config, split_name)
    write_jsonl(data_path, [sample.to_dict() for sample in samples])
    manifest = SplitManifest(
        protocol=FUSION_PROTOCOL,
        split=split_name,
        sample_count=len(samples),
        feature_shape=[2, 129],
        labels=label_distribution(sample.label for sample in samples),
        data_path=str(data_path),
        metadata=metadata,
    )
    write_json(_prepared_manifest_path(config, split_name), manifest.to_dict())
    return manifest


def _build_fusion_rows_for_split(
    config: dict[str, Any],
    split: str,
    can_model,
    eth_model,
    device,
    prepared_dataset: PreparedDatasetFn,
    predict_dataset: PredictDatasetFn,
    close_dataset: CloseDatasetFn,
) -> tuple[list[FusionSample], dict[str, Any]]:
    torch = require_dependency("torch")
    payload = require_fusion_enabled(config)
    inference_batch_size = max(int(config["training"]["batch_size"]), 256)
    can_dataset = prepared_dataset(config, "can", split)
    eth_dataset = prepared_dataset(config, "ethernet", split)
    try:
        can_labels, can_logits, can_probs, can_embeddings = predict_dataset(
            can_model,
            can_dataset,
            "can",
            inference_batch_size,
            device,
        )
        eth_labels, eth_logits, eth_probs, eth_embeddings = predict_dataset(
            eth_model,
            eth_dataset,
            "ethernet",
            inference_batch_size,
            device,
        )
    finally:
        close_dataset(can_dataset)
        close_dataset(eth_dataset)

    can_scores = can_logits if bool(payload["use_raw_logits"]) else can_probs
    eth_scores = eth_logits if bool(payload["use_raw_logits"]) else eth_probs
    can_buckets = _bucket_protocol_outputs(
        "can",
        can_labels,
        can_scores,
        can_embeddings,
        bucket_ms=int(payload["bucket_ms"]),
        pseudo_time_step=float(payload["pseudo_time_step"]),
    )
    eth_buckets = _bucket_protocol_outputs(
        "ethernet",
        eth_labels,
        eth_scores,
        eth_embeddings,
        bucket_ms=int(payload["bucket_ms"]),
        pseudo_time_step=float(payload["pseudo_time_step"]),
    )

    pair_counts, raw_summary = _allocate_pair_type_counts(can_buckets, eth_buckets)
    can_attack_pool = [bucket for bucket in can_buckets if int(bucket["label"]) == 1]
    can_normal_pool = [bucket for bucket in can_buckets if int(bucket["label"]) == 0]
    eth_attack_pool = [bucket for bucket in eth_buckets if int(bucket["label"]) == 1]
    eth_normal_pool = [bucket for bucket in eth_buckets if int(bucket["label"]) == 0]

    can_attack_selected = _select_evenly_spaced(can_attack_pool, pair_counts["AA"] + pair_counts["AN"])
    can_normal_selected = _select_evenly_spaced(can_normal_pool, pair_counts["NA"] + pair_counts["NN"])
    eth_attack_selected = _select_evenly_spaced(eth_attack_pool, pair_counts["AA"] + pair_counts["NA"])
    eth_normal_selected = _select_evenly_spaced(eth_normal_pool, pair_counts["AN"] + pair_counts["NN"])

    can_attack_groups = _partition_selected_pool(
        can_attack_selected,
        [("AA", pair_counts["AA"]), ("AN", pair_counts["AN"])],
    )
    can_normal_groups = _partition_selected_pool(
        can_normal_selected,
        [("NA", pair_counts["NA"]), ("NN", pair_counts["NN"])],
    )
    eth_attack_groups = _partition_selected_pool(
        eth_attack_selected,
        [("AA", pair_counts["AA"]), ("NA", pair_counts["NA"])],
    )
    eth_normal_groups = _partition_selected_pool(
        eth_normal_selected,
        [("AN", pair_counts["AN"]), ("NN", pair_counts["NN"])],
    )

    grouped_can_buckets = {
        "AA": can_attack_groups["AA"],
        "AN": can_attack_groups["AN"],
        "NA": can_normal_groups["NA"],
        "NN": can_normal_groups["NN"],
    }
    grouped_eth_buckets = {
        "AA": eth_attack_groups["AA"],
        "AN": eth_normal_groups["AN"],
        "NA": eth_attack_groups["NA"],
        "NN": eth_normal_groups["NN"],
    }

    rows: list[FusionSample] = []
    bucket_index = 0
    for pair_type in PAIR_TYPE_ORDER:
        can_group = grouped_can_buckets[pair_type]
        eth_group = grouped_eth_buckets[pair_type]
        if len(can_group) != pair_counts[pair_type] or len(eth_group) != pair_counts[pair_type]:
            raise ValueError(f"Pair type {pair_type} allocation is inconsistent with selected protocol buckets")
        for can_bucket, eth_bucket in zip(can_group, eth_group):
            fusion_tensor = stack_expert_outputs(
                [
                    torch.tensor([can_bucket["mean_score"]], dtype=torch.float32),
                    torch.tensor([eth_bucket["mean_score"]], dtype=torch.float32),
                ],
                [
                    torch.tensor([can_bucket["mean_embedding"]], dtype=torch.float32),
                    torch.tensor([eth_bucket["mean_embedding"]], dtype=torch.float32),
                ],
            ).squeeze(0)
            rows.append(
                FusionSample(
                    features=fusion_tensor.tolist(),
                    label=1 if (can_bucket["label"] or eth_bucket["label"]) else 0,
                    bucket_index=bucket_index,
                    can_label=int(can_bucket["label"]),
                    ethernet_label=int(eth_bucket["label"]),
                    pair_type=pair_type,
                    metadata={
                        "expert_order": list(FUSION_EXPERT_ORDER),
                        "pair_type": pair_type,
                        "pairing_method": FUSION_PAIRING_METHOD,
                        "can_bucket_index": int(can_bucket["bucket_index"]),
                        "ethernet_bucket_index": int(eth_bucket["bucket_index"]),
                        "can_member_count": int(can_bucket["member_count"]),
                        "ethernet_member_count": int(eth_bucket["member_count"]),
                        "can_sequence_range": [int(can_bucket["sequence_start"]), int(can_bucket["sequence_end"])],
                        "ethernet_sequence_range": [
                            int(eth_bucket["sequence_start"]),
                            int(eth_bucket["sequence_end"]),
                        ],
                    },
                )
            )
            bucket_index += 1

    paired_summary = fusion_rows_summary([row.to_dict() for row in rows])
    report = {
        "split": split,
        **raw_summary,
        **paired_summary,
    }
    return rows, report


def prepare_fusion_dataset(
    config: dict[str, Any],
    splits: Iterable[str],
    prepared_dataset: PreparedDatasetFn,
    load_exact_model: LoadExactModelFn,
    predict_dataset: PredictDatasetFn,
    resolve_device: ResolveDeviceFn,
    close_dataset: CloseDatasetFn,
) -> dict[str, Any]:
    torch = require_dependency("torch")
    payload = require_fusion_enabled(config)
    protocol_dir = Path(config["artifacts_dir"]) / "prepared" / FUSION_PROTOCOL
    protocol_dir.mkdir(parents=True, exist_ok=True)
    can_model, can_checkpoint = load_exact_model(config, "can", "student")
    eth_model, eth_checkpoint = load_exact_model(config, "ethernet", "student")
    device = resolve_device(torch)

    requested_splits = [str(split) for split in splits]
    split_reports: dict[str, Any] = {}
    split_manifests: dict[str, Any] = {}
    for split in requested_splits:
        rows, report = _build_fusion_rows_for_split(
            config,
            split,
            can_model,
            eth_model,
            device=device,
            prepared_dataset=prepared_dataset,
            predict_dataset=predict_dataset,
            close_dataset=close_dataset,
        )
        manifest = _write_fusion_split(
            config,
            split,
            rows,
            metadata={
                "expert_order": list(FUSION_EXPERT_ORDER),
                "source_protocols": list(FUSION_EXPERT_ORDER),
                "bucket_ms": int(payload["bucket_ms"]),
                "pseudo_time_step": float(payload["pseudo_time_step"]),
                "pairing_method": FUSION_PAIRING_METHOD,
                "surrogate_pairing": FUSION_PAIRING_METHOD,
                "use_raw_logits": bool(payload["use_raw_logits"]),
                "source_model_paths": {
                    "can": str(can_checkpoint),
                    "ethernet": str(eth_checkpoint),
                },
                "summary": report,
            },
        )
        split_reports[split] = report
        split_manifests[split] = manifest.to_dict()

    report_path = _prepared_report_path(config)
    if report_path.exists():
        qa_report = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        qa_report = {
            "protocol": FUSION_PROTOCOL,
            "pairing_method": FUSION_PAIRING_METHOD,
            "expert_order": list(FUSION_EXPERT_ORDER),
            "splits": {},
        }
    qa_report.update(
        {
            "protocol": FUSION_PROTOCOL,
            "pairing_method": FUSION_PAIRING_METHOD,
            "expert_order": list(FUSION_EXPERT_ORDER),
            "bucket_ms": int(payload["bucket_ms"]),
            "pseudo_time_step": float(payload["pseudo_time_step"]),
            "use_raw_logits": bool(payload["use_raw_logits"]),
            "source_model_paths": {
                "can": str(can_checkpoint),
                "ethernet": str(eth_checkpoint),
            },
        }
    )
    qa_report.setdefault("splits", {})
    qa_report["splits"].update(split_reports)
    write_json(report_path, qa_report)
    return {"protocol": FUSION_PROTOCOL, "manifests": split_manifests, "qa": qa_report}


def fusion_eval_extra(config: dict[str, Any], split: str) -> dict[str, Any]:
    manifest_path = _prepared_manifest_path(config, split)
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary = payload.get("metadata", {}).get("summary")
        if isinstance(summary, dict) and summary:
            return summary
    return fusion_rows_summary(read_jsonl(_prepared_split_path(config, split)))
