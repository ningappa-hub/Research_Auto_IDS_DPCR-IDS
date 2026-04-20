"""ONNX Runtime benchmark harness for the fusion head on Raspberry Pi class devices."""

from __future__ import annotations

import argparse
import csv
import ctypes
import importlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from dpcr_ids.utils.deps import require_dependency
from dpcr_ids.utils.fs import ensure_dir
from dpcr_ids.utils.fs import write_json


def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None


def _load_or_generate_input(
    input_json: str | None,
    batch_size: int,
    num_experts: int,
    expert_dim: int,
    seed: int,
):
    numpy = require_dependency("numpy", extra="ml")
    if input_json is not None:
        payload = json.loads(Path(input_json).read_text(encoding="utf-8"))
        return numpy.asarray(payload, dtype=numpy.float32)
    rng = numpy.random.default_rng(seed)
    return rng.standard_normal((batch_size, num_experts, expert_dim)).astype(numpy.float32)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    index = min(max(int(round((percentile / 100.0) * (len(values_sorted) - 1))), 0), len(values_sorted) - 1)
    return float(values_sorted[index])


def _process_rss_bytes(psutil_module=None, process=None) -> int:
    if psutil_module is not None and process is not None:
        return int(process.memory_info().rss)

    if os.name == "nt":
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_uint32),
                ("PageFaultCount", ctypes.c_uint32),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            ctypes.c_uint32,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_bool
        ok = psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
        return int(counters.WorkingSetSize) if ok else 0

    resource = _optional_module("resource")
    if resource is None:
        return 0
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(usage)
    return int(usage * 1024)


def _cpu_percent_sample(start_process_time: float, start_wall_time: float, end_process_time: float, end_wall_time: float) -> float:
    wall_delta = end_wall_time - start_wall_time
    if wall_delta <= 0:
        return 0.0
    process_delta = max(end_process_time - start_process_time, 0.0)
    return max((process_delta / wall_delta) * 100.0, 0.0)


def benchmark_fusion_onnx(
    model_path: str | Path,
    output_json: str | Path,
    output_csv: str | Path | None = None,
    input_json: str | None = None,
    batch_size: int = 1,
    num_experts: int = 2,
    expert_dim: int = 129,
    runs: int = 5,
    warmup_runs: int = 100,
    timed_runs: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    ort = require_dependency("onnxruntime", extra="ml")
    psutil = _optional_module("psutil")

    target = Path(model_path)
    if not target.exists():
        raise FileNotFoundError(f"ONNX model does not exist: {target}")

    sample = _load_or_generate_input(input_json, batch_size, num_experts, expert_dim, seed)
    session = ort.InferenceSession(str(target), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    process = psutil.Process() if psutil is not None else None

    all_latencies: list[float] = []
    per_run_peak_rss: list[float] = []
    cpu_samples: list[float] = []
    for _ in range(runs):
        for _ in range(warmup_runs):
            session.run(None, {input_name: sample})

        peak_rss = _process_rss_bytes(psutil, process)
        if psutil is not None and process is not None:
            process.cpu_percent(interval=None)
        run_latencies: list[float] = []
        process_start = time.process_time()
        wall_start = time.perf_counter()
        for _ in range(timed_runs):
            start = time.perf_counter()
            session.run(None, {input_name: sample})
            run_latencies.append((time.perf_counter() - start) * 1000.0)
            peak_rss = max(peak_rss, _process_rss_bytes(psutil, process))
        process_end = time.process_time()
        wall_end = time.perf_counter()

        all_latencies.extend(run_latencies)
        per_run_peak_rss.append(peak_rss / (1024 * 1024))
        if psutil is not None and process is not None:
            cpu_samples.append(float(process.cpu_percent(interval=None)))
        else:
            cpu_samples.append(_cpu_percent_sample(process_start, wall_start, process_end, wall_end))

    result = {
        "platform": platform.platform(),
        "model_name": target.name,
        "input_shape": [batch_size, num_experts, expert_dim],
        "onnx_size_mb": target.stat().st_size / (1024 * 1024),
        "runs": runs,
        "warmup_runs": warmup_runs,
        "timed_runs": timed_runs,
        "latency_ms_p50": statistics.median(all_latencies) if all_latencies else 0.0,
        "latency_ms_p95": _percentile(all_latencies, 95.0),
        "latency_ms_p99": _percentile(all_latencies, 99.0),
        "latency_ms_mean": statistics.mean(all_latencies) if all_latencies else 0.0,
        "latency_ms_std": statistics.pstdev(all_latencies) if len(all_latencies) > 1 else 0.0,
        "rss_mb_peak": max(per_run_peak_rss) if per_run_peak_rss else 0.0,
        "cpu_percent_mean": statistics.mean(cpu_samples) if cpu_samples else 0.0,
    }
    write_json(output_json, result)

    if output_csv is not None:
        csv_path = Path(output_csv)
        ensure_dir(csv_path.parent)
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result.keys()))
            writer.writeheader()
            writer.writerow(result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dpcr-ids-benchmark-fusion", description="Benchmark a fusion ONNX model")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv")
    parser.add_argument("--input-json")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--num-experts", type=int, default=2)
    parser.add_argument("--expert-dim", type=int, default=129)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup-runs", type=int, default=100)
    parser.add_argument("--timed-runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = benchmark_fusion_onnx(
        model_path=args.model,
        output_json=args.output_json,
        output_csv=args.output_csv,
        input_json=args.input_json,
        batch_size=args.batch_size,
        num_experts=args.num_experts,
        expert_dim=args.expert_dim,
        runs=args.runs,
        warmup_runs=args.warmup_runs,
        timed_runs=args.timed_runs,
        seed=args.seed,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
