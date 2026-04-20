"""Replay prepared IDS splits through saved checkpoints and runtime routing."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from dpcr_ids.config import load_config
from dpcr_ids.runtime.aggregator import DecisionAggregator
from dpcr_ids.runtime.router import ConfidenceRouter
from dpcr_ids.runtime.service import RuntimeIDSService
from dpcr_ids.training.calibration import TemperatureScaler
from dpcr_ids.training.fallback import ProtocolFallbackModel
from dpcr_ids.training.metrics import binary_classification_report
from dpcr_ids.training.metrics import routing_ratio
from dpcr_ids.training.metrics import sigmoid
from dpcr_ids.training.pipeline import _build_loader
from dpcr_ids.training.pipeline import _calibration_path
from dpcr_ids.training.pipeline import _close_dataset
from dpcr_ids.training.pipeline import _fallback_path
from dpcr_ids.training.pipeline import _load_trained_model
from dpcr_ids.training.pipeline import _prepared_dataset
from dpcr_ids.training.pipeline import _resolve_device
from dpcr_ids.utils.deps import require_dependency
from dpcr_ids.utils.fs import write_json

PROTOCOLS = ("can", "ethernet", "fusion")
POSITIVE_DECISIONS = {"ATTACK", "ESCALATE"}


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(max(int(round((pct / 100.0) * (len(ordered) - 1))), 0), len(ordered) - 1)
    return float(ordered[idx])


def value_summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "mean": 0.0, "std": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "p50": statistics.median(values),
        "p95": percentile(values, 95.0),
        "p99": percentile(values, 99.0),
        "max": max(values),
    }


def load_scaler(config: dict[str, Any], protocol: str) -> TemperatureScaler:
    path = _calibration_path(config, protocol)
    if not path.exists():
        return TemperatureScaler(1.0)
    payload = load_config(path)
    return TemperatureScaler(float(payload["temperature"]))


def load_fallback(config: dict[str, Any], protocol: str) -> ProtocolFallbackModel | None:
    if protocol == "fusion":
        return None
    path = _fallback_path(config, protocol)
    return ProtocolFallbackModel.load(path) if path.exists() else None


def sync_device(torch, device) -> None:
    if getattr(device, "type", None) == "cuda":
        torch.cuda.synchronize(device)


def manifest_warnings(config: dict[str, Any], protocol: str, split: str) -> list[str]:
    path = Path(config["artifacts_dir"]) / "prepared" / protocol / f"{split}.manifest.json"
    if not path.exists():
        return [f"{protocol}/{split}: manifest missing; provenance unknown."]
    manifest = load_config(path)
    labels = manifest.get("labels", {})
    warnings: list[str] = []
    if len([label for label, count in labels.items() if int(count) > 0]) < 2:
        warnings.append(f"{protocol}/{split}: only one label class present ({labels}); FPR/AUC are limited.")
    metadata = manifest.get("metadata", {})
    if metadata.get("surrogate_only"):
        warnings.append(f"{protocol}/{split}: manifest marks the split as surrogate_only.")
    if metadata.get("surrogate_pairing"):
        warnings.append(f"{protocol}/{split}: fusion uses {metadata['surrogate_pairing']} rather than live synchronized capture.")
    truncated = metadata.get("summary", {}).get("truncated_can_buckets", 0)
    if truncated:
        warnings.append(f"{protocol}/{split}: fusion pairing truncated {truncated} CAN buckets.")
    return warnings


def build_service(config: dict[str, Any], protocol: str, deadline_ms: float) -> RuntimeIDSService:
    routing = config["routing"]
    return RuntimeIDSService(
        routers={protocol: ConfidenceRouter(float(routing["tau_low"]), float(routing["tau_high"]))},
        aggregator=DecisionAggregator(bucket_ms=int(routing.get("bucket_ms", 250))),
        deadline_ms=deadline_ms,
        fail_open=True,
    )


def warm_model(torch, model, dataset, device, runs: int) -> None:
    if runs <= 0 or len(dataset) == 0:
        return
    features, _ = dataset[0]
    sample = features.unsqueeze(0).to(device)
    with torch.no_grad():
        for _ in range(runs):
            model(sample)
            model.forward_features(sample)
        sync_device(torch, device)


def simulate_protocol(
    config: dict[str, Any],
    protocol: str,
    split: str,
    max_samples: int | None,
    batch_size: int,
    warmup_runs: int,
    deadline_ms: float,
) -> dict[str, Any]:
    torch = require_dependency("torch")
    model, kind, checkpoint = _load_trained_model(config, protocol)
    device = _resolve_device(torch)
    model = model.to(device)
    model.eval()
    scaler = load_scaler(config, protocol)
    fallback = load_fallback(config, protocol)
    service = build_service(config, protocol, deadline_ms)
    dataset = _prepared_dataset(config, protocol, split)

    labels: list[int] = []
    calibrated_probs: list[float] = []
    runtime_probs: list[float] = []
    decisions: list[str] = []
    paths: list[str] = []
    inference_ms: list[float] = []
    routing_ms: list[float] = []
    end_to_end_ms: list[float] = []
    fallback_probs: list[float] = []
    index = 0

    try:
        warm_model(torch, model, dataset, device, warmup_runs)
        pin_memory = getattr(device, "type", None) == "cuda"
        loader = _build_loader(dataset, batch_size=batch_size, shuffle=False, pin_memory=pin_memory)
        with torch.no_grad():
            for features, batch_labels in loader:
                if max_samples is not None and index >= max_samples:
                    break
                features = features.to(device, non_blocking=pin_memory)
                sync_device(torch, device)
                started = time.perf_counter()
                logits = model(features)
                embeddings = model.forward_features(features)
                sync_device(torch, device)
                batch_inference = (time.perf_counter() - started) * 1000.0

                batch_logits = logits.detach().cpu().reshape(-1).tolist()
                batch_embeddings = embeddings.detach().cpu().tolist()
                batch_label_values = batch_labels.detach().cpu().int().tolist()
                per_item_inference = batch_inference / max(len(batch_label_values), 1)

                for logit, embedding, label in zip(batch_logits, batch_embeddings, batch_label_values):
                    if max_samples is not None and index >= max_samples:
                        break
                    sample_started = time.perf_counter()
                    raw_prob = float(sigmoid(float(logit)))
                    cal_prob = scaler.transform_probability(raw_prob)
                    route = service.routers[protocol].route(cal_prob, p_attack_raw=raw_prob)
                    fallback_prob = None
                    if route.decision is None and fallback is not None:
                        fallback_prob = fallback.predict_probability(embedding)
                        fallback_probs.append(fallback_prob)
                    alert = service.process_event(
                        protocol=protocol,
                        raw_probability=raw_prob,
                        calibrated_probability=cal_prob,
                        timestamp=index * float(config.get("fusion", {}).get("pseudo_time_step", 0.01)),
                        metadata={"split": split, "sample_index": index, "label": int(label)},
                        fallback_probability=fallback_prob,
                    )
                    total_ms = (time.perf_counter() - sample_started) * 1000.0 + per_item_inference
                    labels.append(int(label))
                    calibrated_probs.append(cal_prob)
                    runtime_probs.append(1.0 if alert.decision in POSITIVE_DECISIONS else 0.0)
                    decisions.append(alert.decision)
                    paths.append(alert.path)
                    inference_ms.append(per_item_inference)
                    routing_ms.append(alert.latency_ms)
                    end_to_end_ms.append(total_ms)
                    index += 1
    finally:
        _close_dataset(dataset)

    decision_counts = dict(Counter(decisions))
    gateway_alerts = service.aggregator.flush()
    return {
        "protocol": protocol,
        "split": split,
        "checkpoint": str(checkpoint),
        "checkpoint_kind": kind,
        "device": str(device),
        "processed_count": len(labels),
        "batch_size": batch_size,
        "warmup_runs": warmup_runs,
        "temperature": scaler.temperature,
        "fallback_used": fallback is not None,
        "decision_counts": decision_counts,
        "path_counts": dict(Counter(paths)),
        "gateway_aggregated_alert_count": len(gateway_alerts),
        "deadline_ms": deadline_ms,
        "deadline_miss_count": sum(1 for latency in end_to_end_ms if latency > deadline_ms),
        "inference_latency_ms": value_summary(inference_ms),
        "routing_latency_ms": value_summary(routing_ms),
        "end_to_end_latency_ms": value_summary(end_to_end_ms),
        "fallback_probability": value_summary(fallback_probs),
        "model_probability_report": binary_classification_report(labels, calibrated_probs) if labels else {},
        "runtime_decision_report": binary_classification_report(
            labels,
            runtime_probs,
            extra={
                "routing_ratio": routing_ratio(paths),
                "escalate_count": decision_counts.get("ESCALATE", 0),
                "predicted_attack_or_escalate_count": sum(1 for probability in runtime_probs if probability >= 0.5),
            },
        ) if labels else {},
        "warnings": manifest_warnings(config, protocol, split),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/research_pipeline.yaml")
    parser.add_argument("--split", default="test")
    parser.add_argument("--protocol", action="append", choices=PROTOCOLS)
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--warmup-runs", type=int, default=5)
    parser.add_argument("--deadline-ms", type=float, default=20.0)
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_samples is not None and args.max_samples <= 0:
        raise ValueError("--max-samples must be positive when provided")
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    config = load_config(args.config)
    protocols = args.protocol or list(PROTOCOLS)
    reports = {
        protocol: simulate_protocol(
            config=config,
            protocol=protocol,
            split=args.split,
            max_samples=args.max_samples,
            batch_size=args.batch_size,
            warmup_runs=args.warmup_runs,
            deadline_ms=args.deadline_ms,
        )
        for protocol in protocols
    }
    output = Path(args.output) if args.output else Path(config["artifacts_dir"]) / "runtime_simulation" / f"{args.split}_real_model_replay.json"
    payload = {
        "simulation": "prepared_split_real_checkpoint_replay",
        "config": args.config,
        "split": args.split,
        "protocols": protocols,
        "max_samples_per_protocol": args.max_samples,
        "deadline_ms": args.deadline_ms,
        "reports": reports,
        "limitations": [
            "Offline replay of prepared splits, not live bus capture from an ECU or gateway.",
            "Latency is measured on this workstation/Python runtime, not target automotive hardware.",
            "Surrogate Ethernet and pseudo-time fusion metadata limit production false-positive claims.",
        ],
    }
    write_json(output, payload)
    print(json.dumps({**payload, "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
