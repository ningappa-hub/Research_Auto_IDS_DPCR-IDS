"""Replay validation for fusion ONNX models on Raspberry Pi class devices."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import time
from pathlib import Path
from typing import Any

from dpcr_ids.export.benchmark import _cpu_percent_sample
from dpcr_ids.export.benchmark import _optional_module
from dpcr_ids.export.benchmark import _percentile
from dpcr_ids.export.benchmark import _process_rss_bytes
from dpcr_ids.training.calibration import TemperatureScaler
from dpcr_ids.training.evaluate import evaluate_predictions
from dpcr_ids.training.metrics import sigmoid
from dpcr_ids.utils.deps import require_dependency
from dpcr_ids.utils.fs import ensure_dir
from dpcr_ids.utils.fs import read_jsonl
from dpcr_ids.utils.fs import write_json


def _load_temperature(calibration_json: str | None) -> tuple[TemperatureScaler, bool, str | None]:
    if calibration_json is None:
        return TemperatureScaler(1.0), False, None
    payload = json.loads(Path(calibration_json).read_text(encoding="utf-8"))
    return TemperatureScaler(float(payload["temperature"])), True, str(calibration_json)


def _chunk_rows(rows: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [rows[index : index + batch_size] for index in range(0, len(rows), batch_size)]


def replay_fusion_onnx(
    model_path: str | Path,
    dataset_jsonl: str | Path,
    output_json: str | Path,
    output_csv: str | Path | None = None,
    predictions_jsonl: str | Path | None = None,
    calibration_json: str | None = None,
    baseline_report_json: str | None = None,
    batch_size: int = 1,
    threshold: float = 0.5,
    max_samples: int | None = None,
) -> dict[str, Any]:
    numpy = require_dependency("numpy", extra="ml")
    ort = require_dependency("onnxruntime", extra="ml")
    psutil = _optional_module("psutil")

    target = Path(model_path)
    if not target.exists():
        raise FileNotFoundError(f"ONNX model does not exist: {target}")

    rows = read_jsonl(dataset_jsonl)
    if max_samples is not None:
        rows = rows[: max(int(max_samples), 0)]
    if not rows:
        raise ValueError("Replay dataset is empty")
    if int(batch_size) <= 0:
        raise ValueError("batch_size must be positive")

    scaler, calibration_used, calibration_path = _load_temperature(calibration_json)
    session = ort.InferenceSession(str(target), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    process = psutil.Process() if psutil is not None else None

    labels: list[int] = []
    probabilities: list[float] = []
    prediction_rows: list[dict[str, Any]] = []
    latency_ms_samples: list[float] = []
    cpu_samples: list[float] = []
    peak_rss = _process_rss_bytes(psutil, process)

    for batch_index, batch_rows in enumerate(_chunk_rows(rows, int(batch_size))):
        features = numpy.asarray([row["features"] for row in batch_rows], dtype=numpy.float32)
        if psutil is not None and process is not None:
            process.cpu_percent(interval=None)
        process_start = time.process_time()
        wall_start = time.perf_counter()
        call_start = time.perf_counter()
        logits = session.run(None, {input_name: features})[0]
        batch_latency_ms = (time.perf_counter() - call_start) * 1000.0
        process_end = time.process_time()
        wall_end = time.perf_counter()
        cpu_samples.append(
            float(process.cpu_percent(interval=None))
            if psutil is not None and process is not None
            else _cpu_percent_sample(process_start, wall_start, process_end, wall_end)
        )
        peak_rss = max(peak_rss, _process_rss_bytes(psutil, process))

        flattened_logits = numpy.asarray(logits, dtype=numpy.float32).reshape(-1)
        per_sample_latency_ms = batch_latency_ms / max(len(batch_rows), 1)
        for row_index, (row, logit) in enumerate(zip(batch_rows, flattened_logits)):
            probability = sigmoid(float(logit))
            calibrated_probability = scaler.transform_probability(probability)
            labels.append(int(row["label"]))
            probabilities.append(calibrated_probability)
            latency_ms_samples.append(per_sample_latency_ms)
            prediction_rows.append(
                {
                    "sample_index": (batch_index * int(batch_size)) + row_index,
                    "label": int(row["label"]),
                    "logit": float(logit),
                    "probability": float(probability),
                    "calibrated_probability": float(calibrated_probability),
                    "prediction": int(calibrated_probability >= threshold),
                    "latency_ms": per_sample_latency_ms,
                    "pair_type": row.get("pair_type") or row.get("metadata", {}).get("pair_type"),
                }
            )

    report = evaluate_predictions(
        labels,
        probabilities,
        threshold=threshold,
        extra={
            "predicted_attack_count": sum(1 for probability in probabilities if probability >= threshold),
        },
    )
    result: dict[str, Any] = {
        "platform": platform.platform(),
        "model_name": target.name,
        "model_path": str(target),
        "dataset_path": str(dataset_jsonl),
        "sample_count": len(rows),
        "batch_size": int(batch_size),
        "threshold": float(threshold),
        "calibration_used": calibration_used,
        "calibration_path": calibration_path,
        "onnx_size_mb": target.stat().st_size / (1024 * 1024),
        "latency_ms_p50": statistics.median(latency_ms_samples) if latency_ms_samples else 0.0,
        "latency_ms_p95": _percentile(latency_ms_samples, 95.0),
        "latency_ms_p99": _percentile(latency_ms_samples, 99.0),
        "latency_ms_mean": statistics.mean(latency_ms_samples) if latency_ms_samples else 0.0,
        "latency_ms_std": statistics.pstdev(latency_ms_samples) if len(latency_ms_samples) > 1 else 0.0,
        "rss_mb_peak": peak_rss / (1024 * 1024),
        "cpu_percent_mean": statistics.mean(cpu_samples) if cpu_samples else 0.0,
        "report": report,
    }

    if baseline_report_json is not None:
        baseline_payload = json.loads(Path(baseline_report_json).read_text(encoding="utf-8"))
        result["baseline_comparison"] = {
            "baseline_path": str(baseline_report_json),
            "f1_delta": float(report["f1"]) - float(baseline_payload.get("f1", 0.0)),
            "recall_delta": float(report["recall"]) - float(baseline_payload.get("recall", 0.0)),
            "precision_delta": float(report["precision"]) - float(baseline_payload.get("precision", 0.0)),
            "fpr_delta": float(report["fpr"]) - float(baseline_payload.get("fpr", 0.0)),
            "ece_delta": float(report["ece"]) - float(baseline_payload.get("ece", 0.0)),
        }

    write_json(output_json, result)

    if output_csv is not None:
        csv_path = Path(output_csv)
        ensure_dir(csv_path.parent)
        flat_row = {
            key: value
            for key, value in result.items()
            if key != "report" and key != "baseline_comparison"
        }
        flat_row.update({f"report_{key}": value for key, value in report.items()})
        if "baseline_comparison" in result:
            flat_row.update(
                {f"baseline_{key}": value for key, value in result["baseline_comparison"].items()}
            )
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(flat_row.keys()))
            writer.writeheader()
            writer.writerow(flat_row)

    if predictions_jsonl is not None:
        predictions_path = Path(predictions_jsonl)
        ensure_dir(predictions_path.parent)
        with predictions_path.open("w", encoding="utf-8") as handle:
            for row in prediction_rows:
                handle.write(json.dumps(row))
                handle.write("\n")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dpcr-ids-replay-fusion",
        description="Replay prepared fusion samples through a fusion ONNX model",
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv")
    parser.add_argument("--predictions-jsonl")
    parser.add_argument("--calibration-json")
    parser.add_argument("--baseline-report-json")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--max-samples", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = replay_fusion_onnx(
        model_path=args.model,
        dataset_jsonl=args.dataset,
        output_json=args.output_json,
        output_csv=args.output_csv,
        predictions_jsonl=args.predictions_jsonl,
        calibration_json=args.calibration_json,
        baseline_report_json=args.baseline_report_json,
        batch_size=args.batch_size,
        threshold=args.threshold,
        max_samples=args.max_samples,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
