#!/usr/bin/env python3
"""Generate a lightweight HTML dashboard from DPCR-IDS simulation alert CSVs."""

from __future__ import annotations

import argparse
import csv
import html
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev


DECISION_COLORS = {
    "NORMAL": "#2e7d32",
    "ATTACK": "#c62828",
    "ESCALATE": "#f9a825",
}


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.search(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", str(value))
    if not match:
        return default
    return float(match.group(0))


def scenario_name(path: Path) -> str:
    stem = path.stem
    if stem.startswith("ids_alerts_"):
        stem = stem[len("ids_alerts_") :]
    return stem.replace("_", " ").title()


def load_alerts(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize_alerts(path: Path, rows: list[dict[str, str]]) -> dict[str, object]:
    counts = Counter((row.get("decision") or "UNKNOWN").upper() for row in rows)
    latencies = [parse_float(row.get("latency_ms")) for row in rows]
    probs = [parse_float(row.get("p_attack_calibrated")) for row in rows]
    normal_high_prob = sum(
        1
        for row in rows
        if (row.get("decision") or "").upper() == "NORMAL"
        and parse_float(row.get("p_attack_calibrated")) >= 0.85
    )
    modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    if not rows:
        status = "empty CSV"
    elif normal_high_prob:
        status = "check p/decision"
    else:
        status = "ok"
    return {
        "total": len(rows),
        "normal": counts.get("NORMAL", 0),
        "attack": counts.get("ATTACK", 0),
        "escalate": counts.get("ESCALATE", 0),
        "normal_high_prob": normal_high_prob,
        "latency_mean": mean(latencies) if latencies else 0.0,
        "latency_max": max(latencies) if latencies else 0.0,
        "latency_std": pstdev(latencies) if len(latencies) > 1 else 0.0,
        "prob_mean": mean(probs) if probs else 0.0,
        "modified": modified,
        "status": status,
    }


def sampled(rows: list[dict[str, str]], max_points: int) -> list[dict[str, str]]:
    if len(rows) <= max_points:
        return rows
    step = max(1, math.ceil(len(rows) / max_points))
    return rows[::step]


def render_timeline(rows: list[dict[str, str]], max_points: int) -> str:
    points = sampled(rows, max_points)
    if not points:
        return "<p class=\"empty\">No alerts recorded.</p>"

    times = [parse_float(row.get("simtime")) for row in points]
    t_min = min(times)
    t_max = max(times)
    span = max(t_max - t_min, 1e-9)

    circles: list[str] = []
    for row, t in zip(points, times):
        decision = (row.get("decision") or "UNKNOWN").upper()
        color = DECISION_COLORS.get(decision, "#546e7a")
        prob = parse_float(row.get("p_attack_calibrated"))
        latency = parse_float(row.get("latency_ms"))
        x = 30 + ((t - t_min) / span) * 940
        y = 32
        radius = 4.0 if decision == "NORMAL" else 6.0
        title = (
            f"t={t:.4f}s decision={decision} "
            f"p={prob:.3f} latency_ms={latency:.3f}"
        )
        circles.append(
            f"<circle cx=\"{x:.2f}\" cy=\"{y}\" r=\"{radius}\" "
            f"fill=\"{color}\"><title>{html.escape(title)}</title></circle>"
        )

    return (
        "<svg class=\"timeline\" viewBox=\"0 0 1000 64\" role=\"img\" "
        "aria-label=\"alert timeline\">"
        "<line x1=\"30\" y1=\"32\" x2=\"970\" y2=\"32\" stroke=\"#78909c\" "
        "stroke-width=\"2\" />"
        f"<text x=\"30\" y=\"56\">{t_min:.2f}s</text>"
        f"<text x=\"920\" y=\"56\">{t_max:.2f}s</text>"
        + "".join(circles)
        + "</svg>"
    )


def render_html(sections: list[tuple[Path, list[dict[str, str]], dict[str, object]]], max_points: int) -> str:
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary_rows = []
    detail_sections = []

    for path, rows, summary in sections:
        name = scenario_name(path)
        status = str(summary["status"])
        status_class = "status-ok"
        if status == "empty CSV":
            status_class = "status-empty"
        elif status == "check p/decision":
            status_class = "status-check"
        summary_rows.append(
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td class=\"{status_class}\">{html.escape(status)}</td>"
            f"<td>{summary['total']}</td>"
            f"<td>{summary['normal']}</td>"
            f"<td>{summary['attack']}</td>"
            f"<td>{summary['escalate']}</td>"
            f"<td>{summary['latency_mean']:.4f}</td>"
            f"<td>{summary['latency_max']:.4f}</td>"
            f"<td>{summary['prob_mean']:.4f}</td>"
            f"<td>{summary['modified']}</td>"
            "</tr>"
        )
        detail_sections.append(
            "<section class=\"card\">"
            f"<h2>{html.escape(name)}</h2>"
            f"<p><code>{html.escape(str(path))}</code></p>"
            f"<p>Status: <strong>{html.escape(status)}</strong>"
            f" | Last modified: <code>{summary['modified']}</code>"
            f" | NORMAL rows with p_attack >= 0.85: {summary['normal_high_prob']}</p>"
            + render_timeline(rows, max_points)
            + "</section>"
        )

    if not sections:
        summary_rows.append("<tr><td colspan=\"10\">No alert CSV files found.</td></tr>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DPCR-IDS Visual Simulation Dashboard</title>
  <style>
    :root {{
      --bg: #0f1720;
      --panel: #162330;
      --text: #eef5f7;
      --muted: #9fb4c2;
      --line: #2c4254;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Verdana, sans-serif;
      background: radial-gradient(circle at top left, #1f3a4a, var(--bg) 42%);
      color: var(--text);
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px; }}
    h1 {{ margin-bottom: 4px; }}
    p {{ color: var(--muted); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0 28px;
      background: rgba(22, 35, 48, 0.92);
      border: 1px solid var(--line);
    }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; }}
    th {{ color: #b8d4e3; font-weight: 600; }}
    code {{ color: #d8edf5; }}
    .status-ok {{ color: #8fdd9b; }}
    .status-empty {{ color: #b0bec5; }}
    .status-check {{ color: #ffd166; }}
    .card {{
      background: rgba(22, 35, 48, 0.92);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px;
      margin: 18px 0;
      box-shadow: 0 10px 28px rgba(0, 0, 0, 0.22);
    }}
    .timeline {{
      width: 100%;
      height: 88px;
      background: #0b141c;
      border-radius: 10px;
    }}
    .legend {{ display: flex; gap: 18px; flex-wrap: wrap; }}
    .legend span::before {{
      content: "";
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 6px;
    }}
    .normal::before {{ background: #2e7d32; }}
    .attack::before {{ background: #c62828; }}
    .escalate::before {{ background: #f9a825; }}
  </style>
</head>
<body>
<main>
  <h1>DPCR-IDS Visual Simulation Dashboard</h1>
  <p>Generated {html.escape(generated)} from OMNeT++ gateway alert CSV files.</p>
  <p class="legend"><span class="normal">NORMAL</span><span class="attack">ATTACK</span><span class="escalate">ESCALATE</span></p>
  <table>
    <thead>
      <tr>
        <th>Scenario</th><th>Status</th><th>Total</th><th>Normal</th><th>Attack</th><th>Escalate</th>
        <th>Mean Latency ms</th><th>Max Latency ms</th><th>Mean p_attack</th><th>Modified UTC</th>
      </tr>
    </thead>
    <tbody>{''.join(summary_rows)}</tbody>
  </table>
  {''.join(detail_sections)}
</main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="simulations/results", help="Directory containing ids_alerts_*.csv files.")
    parser.add_argument("--pattern", default="ids_alerts_*.csv", help="CSV filename glob to include.")
    parser.add_argument("--output", default="simulations/results/visual_dashboard.html", help="HTML output path.")
    parser.add_argument("--max-points", type=int, default=1200, help="Maximum timeline points per scenario.")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output = Path(args.output)
    paths = sorted(results_dir.glob(args.pattern))

    sections = []
    for path in paths:
        rows = load_alerts(path)
        sections.append((path, rows, summarize_alerts(path, rows)))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(sections, args.max_points), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
