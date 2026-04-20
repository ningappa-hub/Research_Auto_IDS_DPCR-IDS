"""Generate publication-ready tables for the DPCR-IDS paper.

Produces:
  1. Per-attack-type detection rate breakdown (CAN + ETH)
  2. Model complexity summary (params, ONNX size, inference latency)
  3. Distillation ablation comparison
  4. Overall results summary

Usage:
    python generate_paper_tables.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONFIG_PATH = "configs/research_pipeline.yaml"
ARTIFACTS_DIR = Path("artifacts/dpcr_ids_research_v1")
PREPARED_DIR = ARTIFACTS_DIR / "prepared"
MODELS_DIR = ARTIFACTS_DIR / "models"
EXPORT_DIR = ARTIFACTS_DIR / "export"
EVAL_DIR = ARTIFACTS_DIR / "evaluations"
OUTPUT_DIR = ARTIFACTS_DIR / "paper_tables"


def _load_config() -> dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_jsonl_rows(path: Path, max_rows: int | None = None) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if max_rows is not None and i >= max_rows:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _sigmoid(x: float) -> float:
    import math
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for label, pred in zip(labels, predictions):
        if label == 1 and pred == 1:
            tp += 1
        elif label == 0 and pred == 1:
            fp += 1
        elif label == 0 and pred == 0:
            tn += 1
        else:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "dr": recall, "fpr": fpr, "support": tp + fn,
    }


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# 1. Per-Attack-Type Evaluation
# ---------------------------------------------------------------------------

def per_attack_type_evaluation(protocol: str) -> dict[str, Any]:
    """Run inference per attack type on prepared test split."""
    try:
        import torch
    except ImportError:
        print(f"  [SKIP] torch not available, reading from cached evaluation")
        return {}

    from dpcr_ids.models import CanStudentTCN, EthStudentCNN
    from dpcr_ids.training.metrics import sigmoid

    # Load model
    model_path = MODELS_DIR / f"{protocol}_student.pt"
    if not model_path.exists():
        # Try distilled
        model_path = MODELS_DIR / f"{protocol}_student_distilled.pt"
    if not model_path.exists():
        print(f"  [SKIP] No model found for {protocol}")
        return {}

    checkpoint = torch.load(model_path, map_location="cpu")
    if protocol == "can":
        model = CanStudentTCN()
    else:
        model = EthStudentCNN()
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    # Load test data with attack types
    test_path = PREPARED_DIR / protocol / "test.jsonl"
    print(f"  Loading {protocol} test data from {test_path}...")

    attack_type_labels: dict[str, list[int]] = defaultdict(list)
    attack_type_preds: dict[str, list[int]] = defaultdict(list)
    attack_type_probs: dict[str, list[float]] = defaultdict(list)

    batch_features = []
    batch_labels = []
    batch_attack_types = []
    batch_size = 512
    total = 0

    with test_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            batch_features.append(row["features"])
            batch_labels.append(int(row["label"]))
            batch_attack_types.append(str(row.get("attack_type", "normal")))
            total += 1

            if len(batch_features) >= batch_size:
                _process_batch(
                    model, device, batch_features, batch_labels, batch_attack_types,
                    attack_type_labels, attack_type_preds, attack_type_probs, sigmoid,
                )
                batch_features.clear()
                batch_labels.clear()
                batch_attack_types.clear()

            if total % 100000 == 0:
                print(f"    Processed {total} samples...")

    # Process remaining
    if batch_features:
        _process_batch(
            model, device, batch_features, batch_labels, batch_attack_types,
            attack_type_labels, attack_type_preds, attack_type_probs, sigmoid,
        )

    print(f"  Total samples: {total}")

    # Compute per-type metrics
    results: dict[str, Any] = {}
    for attack_type in sorted(attack_type_labels.keys()):
        labels = attack_type_labels[attack_type]
        preds = attack_type_preds[attack_type]
        metrics = _binary_metrics(labels, preds)
        results[attack_type] = metrics

    # Overall
    all_labels = []
    all_preds = []
    for at in attack_type_labels:
        all_labels.extend(attack_type_labels[at])
        all_preds.extend(attack_type_preds[at])
    results["__overall__"] = _binary_metrics(all_labels, all_preds)

    return results


def _process_batch(model, device, features, labels, attack_types,
                   at_labels, at_preds, at_probs, sigmoid_fn):
    import torch
    with torch.no_grad():
        tensor = torch.tensor(features, dtype=torch.float32).to(device)
        logits = model(tensor).cpu().tolist()

    for logit, label, at in zip(logits, labels, attack_types):
        prob = sigmoid_fn(logit)
        pred = 1 if prob >= 0.5 else 0
        at_labels[at].append(label)
        at_preds[at].append(pred)
        at_probs[at].append(prob)


def format_per_attack_table(results: dict[str, Any], protocol: str) -> str:
    """Format per-attack-type results as a markdown table."""
    lines = [
        f"### {protocol.upper()} Per-Attack-Type Detection Rates (Test Set)",
        "",
        "| Attack Type | Support | DR (Recall) | Precision | F1 | FPR |",
        "|---|---|---|---|---|---|",
    ]
    for at in sorted(results.keys()):
        if at == "__overall__":
            continue
        m = results[at]
        lines.append(
            f"| {at} | {m['support']} | {m['dr']:.4f} | {m['precision']:.4f} | {m['f1']:.4f} | {m['fpr']:.4f} |"
        )
    if "__overall__" in results:
        m = results["__overall__"]
        lines.append(
            f"| **Overall** | **{m['support']}** | **{m['dr']:.4f}** | **{m['precision']:.4f}** | **{m['f1']:.4f}** | **{m['fpr']:.4f}** |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. Model Complexity Summary
# ---------------------------------------------------------------------------

def model_complexity_summary() -> str:
    """Compute parameter counts and ONNX sizes for all models."""
    try:
        import torch
    except ImportError:
        return "torch not available — cannot compute parameter counts"

    from dpcr_ids.models import CanStudentTCN, EthStudentCNN, CanTeacherTransformer, EthTeacherTransformer

    try:
        from dpcr_ids.models import TinyLateFusionMetaModel
    except Exception:
        TinyLateFusionMetaModel = None

    # (display name, constructor, onnx file, checkpoint file)
    models_info = [
        ("CAN Student (TCN)", CanStudentTCN, "can_student.onnx", "can_student.pt"),
        ("CAN Teacher (Transformer)", CanTeacherTransformer, None, "can_teacher.pt"),
        ("CAN Distilled (TCN)", CanStudentTCN, None, "can_student_distilled.pt"),
        ("ETH Student (CNN)", EthStudentCNN, "eth_student.onnx", "ethernet_student.pt"),
        ("ETH Teacher (Transformer)", EthTeacherTransformer, None, "ethernet_teacher.pt"),
        ("ETH Distilled (CNN)", EthStudentCNN, None, "ethernet_student_distilled.pt"),
    ]
    if TinyLateFusionMetaModel:
        models_info.append(("Fusion Head (Gated MLP)", TinyLateFusionMetaModel, "fusion_student.onnx", "fusion_student.pt"))

    lines = [
        "### Model Complexity Summary",
        "",
        "| Model | Parameters | Trainable | ONNX Size (KB) | Checkpoint (KB) |",
        "|---|---|---|---|---|",
    ]

    for name, model_cls, onnx_name, ckpt_name in models_info:
        try:
            model = model_cls()
            total_params = sum(p.numel() for p in model.parameters())
            trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

            onnx_size = "—"
            if onnx_name:
                onnx_path = EXPORT_DIR / onnx_name
                if onnx_path.exists():
                    onnx_size = f"{onnx_path.stat().st_size / 1024:.1f}"

            ckpt_size = "—"
            if ckpt_name:
                ckpt_path = MODELS_DIR / ckpt_name
                if ckpt_path.exists():
                    ckpt_size = f"{ckpt_path.stat().st_size / 1024:.1f}"

            lines.append(
                f"| {name} | {total_params:,} | {trainable_params:,} | {onnx_size} | {ckpt_size} |"
            )
        except Exception as e:
            lines.append(f"| {name} | error: {e} | — | — | — |")

    # Total edge parameters
    if TinyLateFusionMetaModel:
        try:
            total_edge = sum(
                sum(p.numel() for p in m.parameters())
                for m in [CanStudentTCN(), EthStudentCNN(), TinyLateFusionMetaModel()]
            )
            lines.append(f"| **Total Edge Deployment** | **{total_edge:,}** | **{total_edge:,}** | — | — |")
        except Exception:
            pass

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. Distillation Ablation
# ---------------------------------------------------------------------------

def distillation_ablation() -> str:
    """Compare student vs distilled vs teacher validation metrics."""
    lines = [
        "### Distillation Ablation (Validation Set)",
        "",
        "| Protocol | Model | Val F1 | Val Precision | Val Recall | Val AUC-ROC |",
        "|---|---|---|---|---|---|",
    ]

    model_kinds = [
        ("can", "teacher", "can_teacher.json"),
        ("can", "student", "can_student.json"),
        ("can", "distilled", "can_student_distilled.json"),
        ("ethernet", "teacher", "ethernet_teacher.json"),
        ("ethernet", "student", "ethernet_student.json"),
        ("ethernet", "distilled", "ethernet_student_distilled.json"),
        ("fusion", "student", "fusion_student.json"),
    ]

    for protocol, kind, filename in model_kinds:
        path = MODELS_DIR / filename
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        val = meta.get("validation", {})
        f1 = val.get("f1", 0)
        prec = val.get("precision", 0)
        rec = val.get("recall", 0)
        auc = val.get("auc_roc", 0)
        auc_str = f"{auc:.4f}" if auc else "—"
        lines.append(
            f"| {protocol} | {kind} | {f1:.4f} | {prec:.4f} | {rec:.4f} | {auc_str} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. Simulation Latency Summary (from .sca files)
# ---------------------------------------------------------------------------

def simulation_latency_summary() -> str:
    """Extract key latency metrics from simulation .sca files."""
    results_dir = Path("dpcr-ids-sim/simulations/results")
    if not results_dir.exists():
        return "Simulation results directory not found"

    configs = ["General", "DoS", "Fuzzy", "GearSpoof", "RpmSpoof", "MultiAttack"]
    lines = [
        "### Simulation Inference Latency (Mean ± Max, ms)",
        "",
        "| Scenario | CAN Inf. (mean) | CAN Inf. (max) | ETH Inf. (mean) | ETH Inf. (max) | Fusion (mean) | Fusion (max) | Router Fast% |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for config in configs:
        can_means, can_maxs = [], []
        eth_means, eth_maxs = [], []
        fus_means, fus_maxs = [], []
        fast_ratios = []

        for rep in range(5):
            sca_path = results_dir / f"{config}-{rep}.sca"
            if not sca_path.exists():
                continue
            content = sca_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "canInferenceMs:mean" in line and "scalar" in line:
                    can_means.append(float(line.split()[-1]))
                elif "canInferenceMs:max" in line and "scalar" in line:
                    can_maxs.append(float(line.split()[-1]))
                elif "ethInferenceMs:mean" in line and "scalar" in line:
                    eth_means.append(float(line.split()[-1]))
                elif "ethInferenceMs:max" in line and "scalar" in line:
                    eth_maxs.append(float(line.split()[-1]))
                elif "fusionInferenceMs:mean" in line and "scalar" in line:
                    fus_means.append(float(line.split()[-1]))
                elif "fusionInferenceMs:max" in line and "scalar" in line:
                    fus_maxs.append(float(line.split()[-1]))
                elif "routingRatioFast" in line and "scalar" in line:
                    fast_ratios.append(float(line.split()[-1]))

        def _avg(lst):
            return sum(lst) / len(lst) if lst else 0

        lines.append(
            f"| {config} | {_avg(can_means):.3f} | {max(can_maxs) if can_maxs else 0:.3f} | "
            f"{_avg(eth_means):.3f} | {max(eth_maxs) if eth_maxs else 0:.3f} | "
            f"{_avg(fus_means):.3f} | {max(fus_maxs) if fus_maxs else 0:.3f} | "
            f"{_avg(fast_ratios)*100:.1f}% |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    _ensure_dir(OUTPUT_DIR)
    report_parts: list[str] = ["# DPCR-IDS Paper-Ready Tables\n"]

    # 1. Per-attack-type evaluation
    print("=" * 60)
    print("1. Per-Attack-Type Evaluation")
    print("=" * 60)

    for protocol in ("can", "ethernet"):
        print(f"\n--- {protocol.upper()} ---")
        results = per_attack_type_evaluation(protocol)
        if results:
            table = format_per_attack_table(results, protocol)
            report_parts.append(table)
            report_parts.append("")

            # Save raw results
            out_path = OUTPUT_DIR / f"{protocol}_per_attack_type.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"  Saved to {out_path}")
            print(table)

    # 2. Model complexity
    print("\n" + "=" * 60)
    print("2. Model Complexity Summary")
    print("=" * 60)
    complexity = model_complexity_summary()
    report_parts.append(complexity)
    report_parts.append("")
    print(complexity)

    # 3. Distillation ablation
    print("\n" + "=" * 60)
    print("3. Distillation Ablation")
    print("=" * 60)
    ablation = distillation_ablation()
    report_parts.append(ablation)
    report_parts.append("")
    print(ablation)

    # 4. Simulation latency
    print("\n" + "=" * 60)
    print("4. Simulation Latency Summary")
    print("=" * 60)
    latency = simulation_latency_summary()
    report_parts.append(latency)
    report_parts.append("")
    print(latency)

    # Write combined report
    report_path = OUTPUT_DIR / "paper_tables.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(report_parts))
    print(f"\n{'=' * 60}")
    print(f"Full report saved to: {report_path}")


if __name__ == "__main__":
    main()
