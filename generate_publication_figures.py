"""Generate publication figures for the DPCR-IDS paper.

The script is intentionally read-only with respect to trained artifacts. It
reads existing JSON/log/simulation outputs and writes derived figures under:

    artifacts/dpcr_ids_research_v1/paper_figures/

It does not import torch, run training, update checkpoints, or rewrite ONNX
exports.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts" / "dpcr_ids_research_v1"
FIGURES = ARTIFACTS / "paper_figures"
MODELS = ARTIFACTS / "models"
EVALUATIONS = ARTIFACTS / "evaluations"
LOGS = ARTIFACTS / "logs"
TABLES = ARTIFACTS / "paper_tables"
RUNTIME = ARTIFACTS / "runtime_simulation"
SIM_RESULTS = ROOT / "dpcr-ids-sim" / "simulations" / "results"


plt.rcParams.update(
    {
        "figure.dpi": 160,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.12,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


@dataclass
class FigureRecord:
    name: str
    files: list[str]
    sources: list[str]
    notes: str = ""


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_figures(dry_run: bool) -> None:
    if not dry_run:
        FIGURES.mkdir(parents=True, exist_ok=True)


def save_figure(
    fig: plt.Figure,
    stem: str,
    records: list[FigureRecord],
    sources: list[Path],
    notes: str = "",
    svg: bool = False,
    dry_run: bool = False,
) -> None:
    files = [FIGURES / f"{stem}.png"]
    if svg:
        files.append(FIGURES / f"{stem}.svg")
    if not dry_run:
        for out in files:
            fig.savefig(out)
    plt.close(fig)
    records.append(
        FigureRecord(
            name=stem,
            files=[rel(p) for p in files],
            sources=[rel(p) for p in sources],
            notes=notes,
        )
    )


def box(
    ax: plt.Axes,
    xy: tuple[float, float],
    wh: tuple[float, float],
    text: str,
    face: str,
    edge: str = "#263238",
    fontsize: int = 9,
) -> None:
    x, y = xy
    w, h = wh
    patch = patches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.018",
        linewidth=1.2,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize)


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    ax.add_patch(
        patches.FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.2,
            color="#37474F",
            shrinkA=4,
            shrinkB=4,
        )
    )


def finish_diagram(ax: plt.Axes, title: str) -> None:
    ax.set_title(title, fontweight="bold", pad=12)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


def generate_system_architecture(records: list[FigureRecord], dry_run: bool) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    box(ax, (0.04, 0.66), (0.18, 0.13), "CAN Bus\nPowertrain, chassis", "#E8F5E9")
    box(ax, (0.04, 0.36), (0.18, 0.13), "Automotive Ethernet\nADAS, infotainment", "#E3F2FD")
    box(ax, (0.29, 0.66), (0.18, 0.13), "CAN feature extractor\n100-frame window\n16 features/frame", "#F1F8E9")
    box(ax, (0.29, 0.36), (0.18, 0.13), "Ethernet extractor\n1024 bytes to\n4 x 32 x 32 image", "#EAF4FF")
    box(ax, (0.54, 0.66), (0.15, 0.13), "CAN student\nTCN\n22,977 params", "#C8E6C9")
    box(ax, (0.54, 0.36), (0.15, 0.13), "Ethernet student\nCNN\n28,321 params", "#BBDEFB")
    box(ax, (0.75, 0.51), (0.16, 0.13), "Confidence router\n0.15 / 0.85\nexpert override", "#E1BEE7")
    box(ax, (0.75, 0.28), (0.16, 0.11), "RF fallback\nfor uncertain\nexpert outputs", "#D7CCC8")
    box(ax, (0.75, 0.73), (0.16, 0.11), "Late fusion head\nGated MLP\n1,459 params", "#FFE0B2")
    box(ax, (0.75, 0.08), (0.16, 0.10), "Decision aggregator\n250 ms buckets", "#ECEFF1")
    box(ax, (0.93, 0.08), (0.06, 0.10), "Alert\noutput", "#FFCDD2", fontsize=8)

    arrow(ax, (0.22, 0.725), (0.29, 0.725))
    arrow(ax, (0.22, 0.425), (0.29, 0.425))
    arrow(ax, (0.47, 0.725), (0.54, 0.725))
    arrow(ax, (0.47, 0.425), (0.54, 0.425))
    arrow(ax, (0.69, 0.725), (0.75, 0.60))
    arrow(ax, (0.69, 0.425), (0.75, 0.56))
    arrow(ax, (0.83, 0.51), (0.83, 0.39))
    arrow(ax, (0.83, 0.39), (0.83, 0.73))
    arrow(ax, (0.83, 0.51), (0.83, 0.18))
    arrow(ax, (0.83, 0.73), (0.83, 0.18))
    arrow(ax, (0.91, 0.13), (0.93, 0.13))

    ax.text(0.66, 0.58, "fast path", fontsize=8, color="#2E7D32")
    ax.text(0.86, 0.45, "uncertain path", fontsize=8, color="#6D4C41")
    finish_diagram(ax, "DPCR-IDS Dual-Protocol Cascade Architecture")
    save_figure(
        fig,
        "fig_architecture_system",
        records,
        [ROOT / "research_presentation.md", ROOT / "configs" / "research_pipeline.yaml"],
        svg=True,
        dry_run=dry_run,
    )


def generate_router_flowchart(records: list[FigureRecord], dry_run: bool) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 7.0))
    box(ax, (0.35, 0.84), (0.30, 0.09), "Expert probabilities\np_can, p_eth", "#ECEFF1")
    box(ax, (0.32, 0.68), (0.36, 0.10), "Expert-aware override\nall experts high-confidence NORMAL?", "#E1F5FE")
    box(ax, (0.06, 0.52), (0.27, 0.10), "Output NORMAL\nfast path", "#C8E6C9")
    box(ax, (0.38, 0.52), (0.24, 0.10), "Threshold test\np < low or p > high", "#F3E5F5")
    box(ax, (0.70, 0.52), (0.24, 0.10), "Output class\nfast path", "#FFCDD2")
    box(ax, (0.38, 0.35), (0.24, 0.10), "RF fallback\non embeddings", "#D7CCC8")
    box(ax, (0.12, 0.19), (0.24, 0.10), "Fallback decides\nNORMAL/ATTACK", "#DCEDC8")
    box(ax, (0.64, 0.19), (0.24, 0.10), "Late fusion\nGated MLP", "#FFE0B2")
    box(ax, (0.38, 0.04), (0.24, 0.10), "Aggregate alerts\n250 ms bucket", "#ECEFF1")

    arrow(ax, (0.50, 0.84), (0.50, 0.78))
    arrow(ax, (0.38, 0.68), (0.22, 0.62))
    arrow(ax, (0.50, 0.68), (0.50, 0.62))
    arrow(ax, (0.62, 0.57), (0.70, 0.57))
    arrow(ax, (0.50, 0.52), (0.50, 0.45))
    arrow(ax, (0.42, 0.35), (0.27, 0.29))
    arrow(ax, (0.58, 0.35), (0.72, 0.29))
    arrow(ax, (0.24, 0.19), (0.43, 0.14))
    arrow(ax, (0.76, 0.19), (0.57, 0.14))
    arrow(ax, (0.18, 0.52), (0.43, 0.14))
    arrow(ax, (0.82, 0.52), (0.57, 0.14))

    ax.text(0.27, 0.64, "yes", fontsize=8)
    ax.text(0.52, 0.64, "no", fontsize=8)
    ax.text(0.63, 0.59, "confident", fontsize=8)
    ax.text(0.52, 0.48, "uncertain", fontsize=8)
    finish_diagram(ax, "Confidence Routing and Escalation Logic")
    save_figure(
        fig,
        "fig_architecture_router_flowchart",
        records,
        [ROOT / "src" / "dpcr_ids" / "runtime" / "router.py", ROOT / "configs" / "research_pipeline.yaml"],
        svg=True,
        dry_run=dry_run,
    )


def generate_model_architecture(records: list[FigureRecord], dry_run: bool) -> None:
    fig, ax = plt.subplots(figsize=(11.0, 5.2))
    ax.text(0.25, 0.93, "CAN Student TCN", ha="center", fontweight="bold", fontsize=12)
    ax.text(0.75, 0.93, "Ethernet Student CNN", ha="center", fontweight="bold", fontsize=12)
    can_steps = [
        ("Input\n16 x 100", "#E8F5E9"),
        ("Depthwise TCN\nchannels 16->32", "#C8E6C9"),
        ("Dilated TCN\n32->64->128", "#A5D6A7"),
        ("Embedding\n128-d", "#81C784"),
        ("Attack logit", "#66BB6A"),
    ]
    eth_steps = [
        ("Input image\n4 x 32 x 32", "#E3F2FD"),
        ("Conv + BN + ReLU\n4->32", "#BBDEFB"),
        ("Conv + BN + ReLU\n32->64", "#90CAF9"),
        ("Projection\n128-d", "#64B5F6"),
        ("Attack logit", "#42A5F5"),
    ]
    for i, (txt, color) in enumerate(can_steps):
        x = 0.04 + i * 0.09
        box(ax, (x, 0.54), (0.08, 0.17), txt, color, fontsize=8)
        if i:
            arrow(ax, (x - 0.01, 0.625), (x, 0.625))
    for i, (txt, color) in enumerate(eth_steps):
        x = 0.54 + i * 0.09
        box(ax, (x, 0.54), (0.08, 0.17), txt, color, fontsize=8)
        if i:
            arrow(ax, (x - 0.01, 0.625), (x, 0.625))

    box(ax, (0.38, 0.18), (0.24, 0.12), "Late fusion input\n2 experts x 129 values", "#FFF3E0")
    box(ax, (0.67, 0.18), (0.20, 0.12), "Gated MLP\n1,459 params", "#FFE0B2")
    arrow(ax, (0.40, 0.54), (0.47, 0.30))
    arrow(ax, (0.90, 0.54), (0.59, 0.30))
    arrow(ax, (0.62, 0.24), (0.67, 0.24))
    ax.text(0.25, 0.42, "22,977 parameters", ha="center", color="#2E7D32", fontweight="bold")
    ax.text(0.75, 0.42, "28,321 parameters", ha="center", color="#1565C0", fontweight="bold")
    finish_diagram(ax, "Student Model Architecture and Fusion Head")
    save_figure(
        fig,
        "fig_architecture_model_components",
        records,
        [ROOT / "src" / "dpcr_ids" / "models"],
        svg=True,
        dry_run=dry_run,
    )


def generate_omnet_topology(records: list[FigureRecord], dry_run: bool) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    box(ax, (0.04, 0.68), (0.17, 0.12), "Sensor ECUs\nCAN traffic", "#E8F5E9")
    box(ax, (0.04, 0.48), (0.17, 0.12), "CAN attackers\nDoS/Fuzzy/Spoof", "#FFEBEE")
    box(ax, (0.04, 0.22), (0.17, 0.12), "ADAS ECUs\nEthernet traffic", "#E3F2FD")
    box(ax, (0.28, 0.58), (0.16, 0.12), "CAN bus hub", "#F1F8E9")
    box(ax, (0.28, 0.25), (0.16, 0.12), "Ethernet hub", "#EAF4FF")
    box(ax, (0.53, 0.64), (0.16, 0.10), "CAN Expert IDS\nONNX Runtime", "#C8E6C9")
    box(ax, (0.53, 0.38), (0.16, 0.10), "Ethernet Expert IDS\nONNX Runtime", "#BBDEFB")
    box(ax, (0.73, 0.52), (0.14, 0.10), "Router", "#E1BEE7")
    box(ax, (0.73, 0.34), (0.14, 0.10), "Fusion IDS", "#FFE0B2")
    box(ax, (0.73, 0.16), (0.14, 0.10), "Aggregator", "#ECEFF1")
    box(ax, (0.91, 0.16), (0.07, 0.10), "Alert\nsink", "#FFCDD2", fontsize=8)
    for start in [(0.21, 0.74), (0.21, 0.54)]:
        arrow(ax, start, (0.28, 0.64))
    arrow(ax, (0.21, 0.28), (0.28, 0.31))
    arrow(ax, (0.44, 0.64), (0.53, 0.69))
    arrow(ax, (0.44, 0.31), (0.53, 0.43))
    arrow(ax, (0.69, 0.69), (0.73, 0.57))
    arrow(ax, (0.69, 0.43), (0.73, 0.57))
    arrow(ax, (0.80, 0.52), (0.80, 0.44))
    arrow(ax, (0.80, 0.34), (0.80, 0.26))
    arrow(ax, (0.87, 0.21), (0.91, 0.21))
    finish_diagram(ax, "OMNeT++ Validation Topology")
    save_figure(
        fig,
        "fig_architecture_omnet_topology",
        records,
        [ROOT / "dpcr-ids-sim" / "src" / "AutomotiveNetwork.ned", ROOT / "dpcr-ids-sim" / "simulations" / "omnetpp.ini"],
        svg=True,
        dry_run=dry_run,
    )


def parse_training_log(path: Path) -> list[dict[str, float | int | str]]:
    if not path.exists():
        return []
    text = ""
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeError:
            continue
    if not text:
        text = path.read_text(encoding="utf-8", errors="ignore")
    rows: list[dict[str, float | int | str]] = []
    pattern = re.compile(
        r"epoch=(?P<epoch>\d+)/(?P<total>\d+).*?"
        r"protocol=(?P<protocol>\w+).*?"
        r"loss=(?P<loss>[0-9.]+).*?"
        r"val_(?P<metric_name>[a-z0-9_]+)=(?P<metric>[0-9.]+).*?"
        r"best_epoch=(?P<best_epoch>\d+)"
    )
    for line in text.splitlines():
        match = pattern.search(line)
        if not match:
            continue
        rows.append(
            {
                "epoch": int(match.group("epoch")),
                "total": int(match.group("total")),
                "protocol": match.group("protocol"),
                "loss": float(match.group("loss")),
                "metric_name": match.group("metric_name"),
                "metric": float(match.group("metric")),
                "best_epoch": int(match.group("best_epoch")),
            }
        )
    return rows


def generate_training_curves(records: list[FigureRecord], dry_run: bool) -> None:
    log_map = {
        "ETH teacher": LOGS / "train_ethernet_teacher.log",
        "ETH student": LOGS / "train_ethernet_student.log",
        "Fusion coverage-aware": LOGS / "train_fusion_coverage_aware.log",
        "Fusion real-TOW": LOGS / "train_fusion_real_tow.log",
    }
    parsed = {label: parse_training_log(path) for label, path in log_map.items()}
    available = {label: rows for label, rows in parsed.items() if rows}
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8))
    colors = ["#C62828", "#1565C0", "#6A1B9A", "#2E7D32"]
    for (label, rows), color in zip(available.items(), colors):
        epochs = [int(r["epoch"]) for r in rows]
        losses = [float(r["loss"]) for r in rows]
        metrics = [float(r["metric"]) for r in rows]
        axes[0].plot(epochs, losses, marker="o", linewidth=1.5, markersize=3, label=label, color=color)
        axes[1].plot(epochs, metrics, marker="o", linewidth=1.5, markersize=3, label=label, color=color)
    axes[0].set_title("Training loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].grid(alpha=0.25)
    axes[1].set_title("Validation F1 from logged runs")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Validation F1")
    axes[1].set_ylim(-0.03, 1.03)
    axes[1].grid(alpha=0.25)
    axes[1].legend(loc="lower right", fontsize=8)
    fig.suptitle("Training Curves Available from Existing Logs", fontweight="bold")
    notes = "CAN epoch-level logs were not present, so CAN curves are not plotted."
    save_figure(fig, "fig_training_curves", records, list(log_map.values()), notes=notes, dry_run=dry_run)


def generate_dataset_figures(records: list[FigureRecord], dry_run: bool) -> None:
    report_path = ARTIFACTS / "prepare_data_report.json"
    report = read_json(report_path, {})
    if not report:
        return

    protocols = [p for p in ("can", "ethernet") if p in report]
    splits = ["train", "val", "test"]

    fig, axes = plt.subplots(1, len(protocols), figsize=(6.1 * max(len(protocols), 1), 4.8), sharey=False)
    if len(protocols) == 1:
        axes = [axes]
    for ax, protocol in zip(axes, protocols):
        manifests = report[protocol].get("manifests", {})
        normal = [int(manifests.get(split, {}).get("labels", {}).get("0", 0)) for split in splits]
        attack = [int(manifests.get(split, {}).get("labels", {}).get("1", 0)) for split in splits]
        x = np.arange(len(splits))
        ax.bar(x, normal, color="#43A047", label="Normal", edgecolor="white")
        ax.bar(x, attack, bottom=normal, color="#C62828", label="Attack", edgecolor="white")
        totals = np.array(normal) + np.array(attack)
        for i, total in enumerate(totals):
            ax.text(i, total * 1.015, f"{int(total):,}", ha="center", fontsize=8)
        ax.set_title(f"{protocol.upper()} prepared split balance")
        ax.set_xticks(x, [s.title() for s in splits])
        ax.set_ylabel("Samples")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(loc="upper right", fontsize=8)
    fig.suptitle("Prepared Dataset Split and Class Balance", fontweight="bold")
    save_figure(fig, "fig_dataset_split_balance", records, [report_path], dry_run=dry_run)

    can_qa = report.get("can", {}).get("qa", {})
    eth_qa = report.get("ethernet", {}).get("qa", {})
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))

    can_files = can_qa.get("files", [])
    can_labels = [item.get("attack_type", "unknown").upper() for item in can_files]
    can_windows = [int(item.get("window_count", 0)) for item in can_files]
    can_tail = [int(item.get("attack_horizon", {}).get("tail_holdout_count", 0)) for item in can_files]
    x = np.arange(len(can_labels))
    axes[0].bar(x, can_windows, color="#1976D2", edgecolor="white", label="All windows")
    axes[0].bar(x, can_tail, color="#90CAF9", edgecolor="white", label="Tail holdout")
    axes[0].set_title("CAN windows by attack file")
    axes[0].set_xticks(x, can_labels)
    axes[0].set_ylabel("Windows")
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].legend(fontsize=8)

    eth_dist = eth_qa.get("raw_label_distribution", {})
    eth_name_map = {
        "normal": "Normal",
        "c_d": "CAN DoS\nTunneled",
        "c_r": "CAN Replay\nTunneled",
        "f_i": "Frame\nInjection",
        "m_f": "MAC\nFlooding",
        "p_i": "PTP\nInjection",
    }
    eth_items = sorted(eth_dist.items(), key=lambda kv: kv[1], reverse=True)
    eth_labels = [eth_name_map.get(k, k) for k, _ in eth_items]
    eth_values = [int(v) for _, v in eth_items]
    colors = ["#43A047" if label == "Normal" else "#C62828" for label in eth_labels]
    axes[1].bar(np.arange(len(eth_labels)), eth_values, color=colors, edgecolor="white")
    axes[1].set_title("Ethernet raw label distribution")
    axes[1].set_xticks(np.arange(len(eth_labels)), eth_labels, fontsize=8)
    axes[1].set_ylabel("Frames")
    axes[1].grid(axis="y", alpha=0.25)
    for i, v in enumerate(eth_values):
        axes[1].text(i, v * 1.015, f"{v / 1000:.0f}K", ha="center", fontsize=8)

    fig.suptitle("Protocol Dataset Composition", fontweight="bold")
    notes = "Uses refreshed prepare-data QA output; no prepared JSONL rows are read by this plotting script."
    save_figure(fig, "fig_dataset_protocol_composition", records, [report_path], notes=notes, dry_run=dry_run)


def generate_confusion_matrices(records: list[FigureRecord], dry_run: bool) -> None:
    files = {
        "CAN": EVALUATIONS / "can.json",
        "Ethernet": EVALUATIONS / "ethernet.json",
        "Fusion": EVALUATIONS / "fusion.json",
    }
    metrics = {name: read_json(path, {}) for name, path in files.items()}
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.1))
    for ax, (name, m) in zip(axes, metrics.items()):
        matrix = np.array([[m.get("tn", 0), m.get("fp", 0)], [m.get("fn", 0), m.get("tp", 0)]], dtype=float)
        display = np.log10(matrix + 1.0)
        im = ax.imshow(display, cmap="Blues")
        total = matrix.sum() or 1.0
        for i in range(2):
            for j in range(2):
                count = int(matrix[i, j])
                pct = 100.0 * matrix[i, j] / total
                ax.text(j, i, f"{count:,}\n{pct:.2f}%", ha="center", va="center", fontsize=9)
        ax.set_title(name)
        ax.set_xticks([0, 1], ["Pred Normal", "Pred Attack"])
        ax.set_yticks([0, 1], ["True Normal", "True Attack"])
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.72, label="log10(count + 1)")
    fig.suptitle("Binary Confusion Matrices on Test Data", fontweight="bold")
    save_figure(fig, "fig_confusion_matrices", records, list(files.values()), dry_run=dry_run)


def generate_per_attack_detection(records: list[FigureRecord], dry_run: bool) -> None:
    can_path = TABLES / "can_per_attack_type.json"
    eth_path = TABLES / "ethernet_per_attack_type.json"
    can = read_json(can_path, {})
    eth = read_json(eth_path, {})
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.7), sharey=True)
    for ax, title, data in [(axes[0], "CAN attacks", can), (axes[1], "Ethernet attacks", eth)]:
        items = [(k, v) for k, v in data.items() if not k.startswith("__") and k != "normal"]
        labels = [k.replace("_", "\n") for k, _ in items]
        dr = [float(v.get("dr", 0.0)) for _, v in items]
        colors = ["#D32F2F" if k == "can_dos_tunneled" else "#1976D2" for k, _ in items]
        ax.bar(np.arange(len(items)), dr, color=colors, edgecolor="white")
        ax.set_title(title)
        ax.set_xticks(np.arange(len(items)), labels, rotation=0, fontsize=8)
        ax.set_ylabel("Detection rate")
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.25)
        for i, v in enumerate(dr):
            ax.text(i, min(v + 0.03, 1.02), f"{v * 100:.1f}%", ha="center", fontsize=8)
    fig.suptitle("Per-Attack Detection Rate Breakdown", fontweight="bold")
    save_figure(fig, "fig_per_attack_detection_rates", records, [can_path, eth_path], dry_run=dry_run)


def generate_tunneled_dos_failure(records: list[FigureRecord], dry_run: bool) -> None:
    eth_path = TABLES / "ethernet_per_attack_type.json"
    eth = read_json(eth_path, {})
    items = [(k, v) for k, v in eth.items() if not k.startswith("__") and k != "normal"]
    labels = [k.replace("_", "\n") for k, _ in items]
    dr = np.array([float(v.get("dr", 0.0)) for _, v in items])
    fn = np.array([int(v.get("fn", 0)) for _, v in items])
    colors = ["#C62828" if k == "can_dos_tunneled" else "#78909C" for k, _ in items]
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.6))
    axes[0].bar(np.arange(len(items)), dr, color=colors, edgecolor="white")
    axes[0].set_title("Ethernet detection rate")
    axes[0].set_ylabel("Detection rate")
    axes[0].set_ylim(0, 1.05)
    axes[0].set_xticks(np.arange(len(items)), labels, fontsize=8)
    axes[0].grid(axis="y", alpha=0.25)
    axes[1].bar(np.arange(len(items)), fn, color=colors, edgecolor="white")
    axes[1].set_title("False negatives by attack type")
    axes[1].set_ylabel("False negatives")
    axes[1].set_xticks(np.arange(len(items)), labels, fontsize=8)
    axes[1].grid(axis="y", alpha=0.25)
    for ax in axes:
        ax.tick_params(axis="x", labelrotation=0)
    fig.suptitle("Failure Case: CAN DoS Tunneled over Ethernet", fontweight="bold")
    save_figure(
        fig,
        "fig_failure_can_dos_tunneled",
        records,
        [eth_path],
        notes="Highlights the Ethernet blind spot caused by the tunneled CAN DoS class.",
        dry_run=dry_run,
    )


def generate_complexity_and_ablation(records: list[FigureRecord], dry_run: bool) -> None:
    model_specs = [
        ("CAN Teacher", 795393, "#8E24AA"),
        ("ETH Teacher", 801537, "#6A1B9A"),
        ("CAN Student", 22977, "#43A047"),
        ("ETH Student", 28321, "#1E88E5"),
        ("Fusion", 1459, "#FB8C00"),
    ]
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    labels = [x[0] for x in model_specs]
    params = [x[1] for x in model_specs]
    colors = [x[2] for x in model_specs]
    ax.bar(np.arange(len(params)), params, color=colors, edgecolor="white")
    ax.set_yscale("log")
    ax.set_ylabel("Parameters (log scale)")
    ax.set_title("Model Complexity Compression")
    ax.set_xticks(np.arange(len(params)), labels, rotation=25, ha="right")
    ax.grid(axis="y", alpha=0.25)
    for i, value in enumerate(params):
        ax.text(i, value * 1.12, f"{value:,}", ha="center", fontsize=8)
    save_figure(
        fig,
        "fig_model_complexity",
        records,
        [TABLES / "paper_tables.md", MODELS / "can_student.json", MODELS / "ethernet_student.json", MODELS / "fusion_student.json"],
        dry_run=dry_run,
    )

    model_jsons = [
        ("CAN teacher", MODELS / "can_teacher.json"),
        ("CAN student", MODELS / "can_student.json"),
        ("CAN distilled", MODELS / "can_student_distilled.json"),
        ("ETH teacher", MODELS / "ethernet_teacher.json"),
        ("ETH student", MODELS / "ethernet_student.json"),
        ("ETH distilled", MODELS / "ethernet_student_distilled.json"),
        ("Fusion", MODELS / "fusion_student.json"),
    ]
    labels = []
    f1 = []
    auc_pr = []
    for label, path in model_jsons:
        data = read_json(path, {})
        val = data.get("validation", {})
        labels.append(label)
        f1.append(float(val.get("f1", 0.0)))
        auc_pr.append(float(val.get("auc_pr", 0.0)))
    x = np.arange(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    ax.bar(x - width / 2, f1, width, label="Validation F1", color="#1976D2", edgecolor="white")
    ax.bar(x + width / 2, auc_pr, width, label="Validation AUC-PR", color="#F57C00", edgecolor="white")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.set_ylabel("Score")
    ax.set_title("Teacher, Student, and Distilled Model Ablation")
    ax.legend(loc="lower right")
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "fig_distillation_ablation", records, [p for _, p in model_jsons], dry_run=dry_run)


def generate_runtime_figures(records: list[FigureRecord], dry_run: bool) -> None:
    runtime_path = RUNTIME / "test_real_model_replay.json"
    runtime = read_json(runtime_path, {})
    reports = runtime.get("reports", {})
    protocols = [p for p in ["can", "ethernet", "fusion"] if p in reports]
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    x = np.arange(len(protocols))
    width = 0.23
    for offset, percentile, color in [(-width, "p50", "#43A047"), (0.0, "p95", "#1E88E5"), (width, "p99", "#F57C00")]:
        values = [float(reports[p].get("end_to_end_latency_ms", {}).get(percentile, 0.0)) for p in protocols]
        ax.bar(x + offset, values, width, label=percentile.upper(), color=color, edgecolor="white")
    ax.axhline(20.0, color="#C62828", linestyle="--", linewidth=1.2, label="20 ms deadline")
    ax.set_xticks(x, [p.upper() for p in protocols])
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Runtime Replay Latency Percentiles")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "fig_runtime_latency_percentiles", records, [runtime_path], dry_run=dry_run)

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    fast = [int(reports[p].get("path_counts", {}).get("fast", 0)) for p in protocols]
    heavy = [int(reports[p].get("path_counts", {}).get("heavy", 0)) for p in protocols]
    totals = np.array(fast) + np.array(heavy)
    fast_pct = np.divide(fast, totals, out=np.zeros_like(totals, dtype=float), where=totals > 0) * 100
    heavy_pct = np.divide(heavy, totals, out=np.zeros_like(totals, dtype=float), where=totals > 0) * 100
    ax.barh(protocols, fast_pct, color="#43A047", label="Fast path")
    ax.barh(protocols, heavy_pct, left=fast_pct, color="#FFB300", label="Heavy path")
    for i, (f, h) in enumerate(zip(fast_pct, heavy_pct)):
        ax.text(min(f / 2, 98), i, f"{f:.1f}%", va="center", ha="center", color="white", fontsize=9)
        if h > 0.2:
            ax.text(f + h / 2, i, f"{h:.1f}%", va="center", ha="center", fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Samples (%)")
    ax.set_title("Cascade Routing Efficiency")
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.25)
    save_figure(fig, "fig_routing_efficiency_flow", records, [runtime_path], dry_run=dry_run)

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    metrics = {
        "CAN": read_json(EVALUATIONS / "can.json", {}),
        "Ethernet": read_json(EVALUATIONS / "ethernet.json", {}),
        "Fusion": read_json(EVALUATIONS / "fusion.json", {}),
    }
    labels = list(metrics.keys())
    ece = [float(metrics[k].get("ece", 0.0)) for k in labels]
    ax.bar(labels, ece, color=["#43A047", "#1E88E5", "#FB8C00"], edgecolor="white")
    ax.set_ylabel("Expected calibration error")
    ax.set_title("Calibration Quality by Model")
    ax.grid(axis="y", alpha=0.25)
    for i, v in enumerate(ece):
        ax.text(i, v + 0.02, f"{v:.3f}", ha="center")
    save_figure(fig, "fig_calibration_ece", records, [EVALUATIONS / "can.json", EVALUATIONS / "ethernet.json", EVALUATIONS / "fusion.json"], dry_run=dry_run)


def parse_sca(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith("scalar "):
            continue
        parts = line.split(None, 3)
        if len(parts) != 4:
            continue
        try:
            out[f"{parts[1]}.{parts[2]}"] = float(parts[3])
        except ValueError:
            pass
    return out


def generate_simulation_summary(records: list[FigureRecord], dry_run: bool) -> None:
    sca_files = sorted(SIM_RESULTS.glob("*.sca"))
    grouped: dict[str, list[dict[str, float]]] = {}
    for path in sca_files:
        match = re.match(r"(.+)-\d+\.sca$", path.name)
        if not match:
            continue
        grouped.setdefault(match.group(1), []).append(parse_sca(path))
    if not grouped:
        return
    names = sorted(grouped.keys())
    mean_lat = [
        np.mean([s.get("AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:mean", 0.0) for s in grouped[n]])
        for n in names
    ]
    max_lat = [
        np.max([s.get("AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:max", 0.0) for s in grouped[n]])
        for n in names
    ]
    fig, ax = plt.subplots(figsize=(9.2, 4.7))
    x = np.arange(len(names))
    ax.bar(x - 0.18, mean_lat, 0.36, label="Mean aggregation E2E", color="#1976D2", edgecolor="white")
    ax.bar(x + 0.18, max_lat, 0.36, label="Max aggregation E2E", color="#D84315", edgecolor="white")
    ax.set_xticks(x, names, rotation=25, ha="right")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Available OMNeT++ Aggregation Latency")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    notes = "Uses only .sca files currently present. This is aggregation E2E latency, not pure model inference latency."
    save_figure(fig, "fig_simulation_available_latency", records, sca_files, notes=notes, dry_run=dry_run)


def write_manifest(records: list[FigureRecord], dry_run: bool) -> None:
    lines = [
        "# DPCR-IDS Publication Figure Manifest",
        "",
        "Generated by `generate_publication_figures.py`.",
        "",
        "## Safety",
        "",
        "- Reads existing artifacts only.",
        "- Does not train models.",
        "- Does not rewrite checkpoints, ONNX exports, fallback models, prepared data, or evaluation JSON files.",
        "",
        "## Figures",
        "",
    ]
    for rec in records:
        lines.append(f"### {rec.name}")
        lines.append("")
        lines.append("Files:")
        for file in rec.files:
            lines.append(f"- `{file}`")
        lines.append("")
        lines.append("Sources:")
        for source in rec.sources:
            lines.append(f"- `{source}`")
        if rec.notes:
            lines.append("")
            lines.append(f"Notes: {rec.notes}")
        lines.append("")
    can_logs = sorted(LOGS.glob("*can*train*.log"))
    if not can_logs:
        lines.extend(
            [
                "## Caveats",
                "",
                "- CAN epoch-level training logs were not found, so CAN training curves are intentionally omitted.",
                "- Some OMNeT++ scenario scalar files are not present in the current results folder; simulation summary figures include only available `.sca` files.",
                "- Runtime replay latency and OMNeT++ aggregation latency are separate quantities and should not be merged in paper text.",
                "",
            ]
        )
    if dry_run:
        print("\n".join(lines[:80]))
    else:
        (FIGURES / "figure_manifest.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate DPCR-IDS paper figures from existing artifacts.")
    parser.add_argument("--dry-run", action="store_true", help="List expected outputs without writing files.")
    args = parser.parse_args()

    ensure_figures(args.dry_run)
    records: list[FigureRecord] = []

    generate_system_architecture(records, args.dry_run)
    generate_router_flowchart(records, args.dry_run)
    generate_model_architecture(records, args.dry_run)
    generate_omnet_topology(records, args.dry_run)
    generate_training_curves(records, args.dry_run)
    generate_dataset_figures(records, args.dry_run)
    generate_confusion_matrices(records, args.dry_run)
    generate_per_attack_detection(records, args.dry_run)
    generate_tunneled_dos_failure(records, args.dry_run)
    generate_complexity_and_ablation(records, args.dry_run)
    generate_runtime_figures(records, args.dry_run)
    generate_simulation_summary(records, args.dry_run)
    write_manifest(records, args.dry_run)

    if args.dry_run:
        print(f"\nDry run complete. Planned figures: {len(records)}")
    else:
        print(f"Generated {len(records)} figure groups in {FIGURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
