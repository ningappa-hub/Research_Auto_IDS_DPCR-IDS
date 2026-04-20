"""Command-line interface for DPCR-IDS."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from dpcr_ids.training.pipeline import calibrate_from_path
from dpcr_ids.training.pipeline import distill_from_path
from dpcr_ids.training.pipeline import evaluate_from_path
from dpcr_ids.training.pipeline import export_onnx_from_path
from dpcr_ids.training.pipeline import prepare_data_from_path
from dpcr_ids.training.pipeline import serve_runtime_from_path
from dpcr_ids.training.pipeline import train_fallback_from_path
from dpcr_ids.training.pipeline import train_student_from_path
from dpcr_ids.training.pipeline import train_teacher_from_path


PROTOCOL_CHOICES = ("can", "ethernet", "fusion")


def _print(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dpcr-ids", description="DPCR-IDS research pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-data", help="Prepare datasets and manifests")
    prepare.add_argument("--config", required=True)
    prepare.add_argument("--protocol", choices=("can", "ethernet", "all"), default="all")

    for name, help_text in [
        ("train-student", "Train a student model"),
        ("train-teacher", "Train a teacher model"),
        ("distill", "Distill a student from a trained teacher"),
        ("calibrate", "Fit temperature scaling on validation logits"),
        ("train-fallback", "Train a protocol-specific fallback model"),
        ("evaluate", "Evaluate a trained system on the test split"),
        ("export-onnx", "Export a trained student model to ONNX"),
    ]:
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--config", required=True)
        command.add_argument("--protocol", required=True, choices=PROTOCOL_CHOICES)

    runtime = subparsers.add_parser("serve-runtime", help="Build the runtime service or simulate one event")
    runtime.add_argument("--config", required=True)
    runtime.add_argument("--protocol", choices=("can", "ethernet"))
    runtime.add_argument("--probability", type=float)
    runtime.add_argument("--timestamp", type=float)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "prepare-data":
            protocol = None if args.protocol == "all" else args.protocol
            return _print(prepare_data_from_path(args.config, protocol=protocol))
        if args.command == "train-student":
            return _print(train_student_from_path(args.config, args.protocol))
        if args.command == "train-teacher":
            return _print(train_teacher_from_path(args.config, args.protocol))
        if args.command == "distill":
            return _print(distill_from_path(args.config, args.protocol))
        if args.command == "calibrate":
            return _print(calibrate_from_path(args.config, args.protocol))
        if args.command == "train-fallback":
            return _print(train_fallback_from_path(args.config, args.protocol))
        if args.command == "evaluate":
            return _print(evaluate_from_path(args.config, args.protocol))
        if args.command == "export-onnx":
            return _print(export_onnx_from_path(args.config, args.protocol))
        if args.command == "serve-runtime":
            return _print(serve_runtime_from_path(args.config, protocol=args.protocol, probability=args.probability, timestamp=args.timestamp))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
