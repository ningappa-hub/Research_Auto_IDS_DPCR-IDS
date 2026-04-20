"""
analyze_simulation_results.py — Parse and visualize DPCR-IDS OMNeT++ results.

Reads .sca (scalar) files and CSV alert logs to produce publication-quality
analysis of the IDS performance across all simulation configurations.

Usage:
    python analyze_simulation_results.py [--results-dir simulations/results]
"""

import argparse
import csv
import os
import re
from pathlib import Path
from collections import defaultdict

# Try to import plotting libraries (optional)
try:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    import numpy as np
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False
    print("[WARN] matplotlib/numpy not found. Text analysis only (no plots).")


def parse_sca_file(filepath: str) -> dict:
    """Parse OMNeT++ .sca file into a dict of {module.metric: value}."""
    scalars = {}
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('scalar '):
                parts = line.strip().split(None, 3)
                if len(parts) >= 4:
                    module = parts[1]
                    metric = parts[2]
                    try:
                        value = float(parts[3])
                    except ValueError:
                        value = parts[3]
                    scalars[f"{module}.{metric}"] = value
    return scalars


def parse_csv_alerts(filepath: str) -> list:
    """Parse IDS alert CSV into list of dicts."""
    alerts = []
    if not os.path.exists(filepath):
        return alerts
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            alerts.append({
                'simtime': float(row['simtime']),
                'decision': row['decision'],
                'path': row['path'],
                'p_attack_raw': float(row['p_attack_raw']),
                'p_attack_calibrated': float(row['p_attack_calibrated']),
                'latency_ms': float(row['latency_ms']),
                'escalate': row['escalate'] == 'true',
            })
    return alerts


def find_configs(results_dir: str) -> dict:
    """Find all simulation configs and their run files."""
    configs = defaultdict(list)
    for f in sorted(os.listdir(results_dir)):
        if f.endswith('.sca'):
            match = re.match(r'^(.+)-(\d+)\.sca$', f)
            if match:
                config_name = match.group(1)
                run_num = int(match.group(2))
                configs[config_name].append({
                    'run': run_num,
                    'sca': os.path.join(results_dir, f),
                    'vec': os.path.join(results_dir, f.replace('.sca', '.vec')),
                })
    return dict(configs)


def analyze_config(config_name: str, runs: list, results_dir: str):
    """Analyze all runs of a single configuration."""
    print(f"\n{'='*70}")
    print(f"  Configuration: {config_name} ({len(runs)} runs)")
    print(f"{'='*70}")

    # Aggregate scalars across runs
    all_scalars = []
    for run in runs:
        scalars = parse_sca_file(run['sca'])
        all_scalars.append(scalars)

    # Key metrics to report
    metrics = [
        ("CAN frames received", "AutomotiveNetwork.gateway.canExpert.framesReceived"),
        ("CAN windows processed", "AutomotiveNetwork.gateway.canExpert.windowsProcessed"),
        ("CAN inference (ms)", "AutomotiveNetwork.gateway.canExpert.canInferenceMs:mean"),
        ("ETH frames processed", "AutomotiveNetwork.gateway.ethExpert.framesProcessed"),
        ("ETH inference (ms)", "AutomotiveNetwork.gateway.ethExpert.ethInferenceMs:mean"),
        ("Fusion pairings", "AutomotiveNetwork.gateway.fusion.fusionsPaired"),
        ("Fusion logit mean", "AutomotiveNetwork.gateway.fusion.fusionLogit:mean"),
        ("Router NORMAL", "AutomotiveNetwork.gateway.router.normalCount"),
        ("Router ATTACK", "AutomotiveNetwork.gateway.router.attackCount"),
        ("Router ESCALATE", "AutomotiveNetwork.gateway.router.escalateCount"),
        ("Fast path ratio", "AutomotiveNetwork.gateway.router.routingRatioFast"),
        ("E2E latency mean (ms)", "AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:mean"),
        ("E2E latency max (ms)", "AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:max"),
        ("Total alerts", "AutomotiveNetwork.gateway.aggregator.totalAlerts"),
        ("Gateway alerts", "AutomotiveNetwork.gateway.aggregator.totalFlushed"),
    ]

    # DoS-specific
    dos_key = "AutomotiveNetwork.dosAttacker.dosFramesSent"
    if dos_key in all_scalars[0]:
        metrics.insert(0, ("DoS frames injected", dos_key))

    print(f"\n  {'Metric':<30} {'Mean':>12} {'Std':>12} {'Min':>12} {'Max':>12}")
    print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")

    for label, key in metrics:
        values = [s.get(key, None) for s in all_scalars]
        values = [v for v in values if v is not None and isinstance(v, (int, float))]
        if values:
            mean = sum(values) / len(values)
            min_v = min(values)
            max_v = max(values)
            if len(values) > 1:
                std = (sum((x - mean) ** 2 for x in values) / (len(values) - 1)) ** 0.5
            else:
                std = 0.0
            print(f"  {label:<30} {mean:>12.2f} {std:>12.4f} {min_v:>12.2f} {max_v:>12.2f}")

    # Parse alert CSV
    csv_files = {
        'General': 'ids_alerts_general.csv',
        'DoS': 'ids_alerts_dos.csv',
        'Fuzzy': 'ids_alerts_fuzzy.csv',
        'GearSpoof': 'ids_alerts_gear_spoof.csv',
        'RpmSpoof': 'ids_alerts_rpm_spoof.csv',
        'MultiAttack': 'ids_alerts_multi.csv',
    }
    csv_name = csv_files.get(config_name, f'ids_alerts_{config_name.lower()}.csv')
    csv_path = os.path.join(results_dir, csv_name)
    alerts = parse_csv_alerts(csv_path)

    if alerts:
        print(f"\n  Alert Timeline ({len(alerts)} gateway alerts):")
        decisions = defaultdict(int)
        for a in alerts:
            decisions[a['decision']] += 1

        for dec, cnt in sorted(decisions.items()):
            pct = cnt / len(alerts) * 100
            print(f"    {dec}: {cnt} ({pct:.1f}%)")

        # Check for decision transitions (attack detection timeline)
        if len(alerts) > 1:
            transitions = []
            for i in range(1, len(alerts)):
                if alerts[i]['decision'] != alerts[i-1]['decision']:
                    transitions.append({
                        'time': alerts[i]['simtime'],
                        'from': alerts[i-1]['decision'],
                        'to': alerts[i]['decision'],
                    })
            if transitions:
                print(f"\n  Decision transitions:")
                for t in transitions[:10]:
                    print(f"    t={t['time']:.3f}s: {t['from']} -> {t['to']}")

    return all_scalars, alerts


def plot_results(all_configs: dict, results_dir: str):
    """Generate publication figures."""
    if not HAS_PLOT:
        return

    output_dir = os.path.join(results_dir, 'figures')
    os.makedirs(output_dir, exist_ok=True)

    # --- Figure 1: E2E Latency Comparison ---
    fig, ax = plt.subplots(figsize=(10, 6))
    configs_with_latency = []
    latencies_mean = []
    latencies_max = []

    for config_name, (scalars_list, alerts) in all_configs.items():
        mean_vals = [s.get("AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:mean", 0)
                     for s in scalars_list]
        max_vals = [s.get("AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:max", 0)
                    for s in scalars_list]
        mean_vals = [v for v in mean_vals if isinstance(v, (int, float))]
        max_vals = [v for v in max_vals if isinstance(v, (int, float))]
        if mean_vals:
            configs_with_latency.append(config_name)
            latencies_mean.append(np.mean(mean_vals))
            latencies_max.append(np.mean(max_vals))

    if configs_with_latency:
        x = np.arange(len(configs_with_latency))
        width = 0.35
        ax.bar(x - width/2, latencies_mean, width, label='Mean E2E', color='#2196F3')
        ax.bar(x + width/2, latencies_max, width, label='Max E2E', color='#FF5722')
        ax.set_xlabel('Configuration')
        ax.set_ylabel('End-to-End Latency (ms)')
        ax.set_title('DPCR-IDS End-to-End Detection Latency')
        ax.set_xticks(x)
        ax.set_xticklabels(configs_with_latency, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, 'e2e_latency_comparison.png'), dpi=150)
        print(f"\n  Saved: {output_dir}/e2e_latency_comparison.png")

    # --- Figure 2: Routing Decision Distribution ---
    fig, axes = plt.subplots(1, len(all_configs), figsize=(5 * len(all_configs), 5))
    if len(all_configs) == 1:
        axes = [axes]

    for idx, (config_name, (scalars_list, alerts)) in enumerate(all_configs.items()):
        s = scalars_list[0]
        normal = s.get("AutomotiveNetwork.gateway.router.normalCount", 0)
        attack = s.get("AutomotiveNetwork.gateway.router.attackCount", 0)
        escalate = s.get("AutomotiveNetwork.gateway.router.escalateCount", 0)

        values = [normal, attack, escalate]
        labels = ['NORMAL', 'ATTACK', 'ESCALATE']
        colors = ['#4CAF50', '#F44336', '#FF9800']

        # Filter out zeros
        filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
        if filtered:
            fl, fv, fc = zip(*filtered)
            axes[idx].pie(fv, labels=fl, colors=fc, autopct='%1.1f%%', startangle=90)
        axes[idx].set_title(f'{config_name}')

    fig.suptitle('DPCR-IDS Routing Decision Distribution', fontsize=14)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'routing_decisions.png'), dpi=150)
    print(f"  Saved: {output_dir}/routing_decisions.png")

    # --- Figure 3: Alert Timeline (for DoS config) ---
    for config_name, (_, alerts) in all_configs.items():
        if alerts and len(alerts) > 5:
            fig, ax = plt.subplots(figsize=(12, 4))
            times = [a['simtime'] for a in alerts]
            probs = [a['p_attack_calibrated'] for a in alerts]
            colors_map = {'NORMAL': '#4CAF50', 'ATTACK': '#F44336', 'ESCALATE': '#FF9800'}
            c = [colors_map.get(a['decision'], '#999') for a in alerts]

            ax.scatter(times, probs, c=c, s=30, alpha=0.8, edgecolors='black', linewidths=0.5)
            ax.axhline(y=0.85, color='red', linestyle='--', alpha=0.5, label='tau_high=0.85')
            ax.axhline(y=0.15, color='green', linestyle='--', alpha=0.5, label='tau_low=0.15')
            ax.set_xlabel('Simulation Time (s)')
            ax.set_ylabel('Calibrated P(attack)')
            ax.set_title(f'DPCR-IDS Alert Timeline — {config_name}')
            ax.legend()
            ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(os.path.join(output_dir, f'timeline_{config_name.lower()}.png'), dpi=150)
            print(f"  Saved: {output_dir}/timeline_{config_name.lower()}.png")

    plt.close('all')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir',
                        default='dpcr-ids-sim/simulations/results',
                        help='Directory containing .sca and .csv result files')
    args = parser.parse_args()

    results_dir = args.results_dir
    if not os.path.isdir(results_dir):
        print(f"ERROR: Results directory not found: {results_dir}")
        return

    configs = find_configs(results_dir)
    print(f"Found {len(configs)} configurations: {', '.join(configs.keys())}")

    all_configs = {}
    for config_name, runs in sorted(configs.items()):
        scalars, alerts = analyze_config(config_name, runs, results_dir)
        all_configs[config_name] = (scalars, alerts)

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  Total configs analyzed: {len(configs)}")
    total_runs = sum(len(runs) for runs in configs.values())
    print(f"  Total simulation runs: {total_runs}")

    # Check stub vs real mode
    first_scalars = list(all_configs.values())[0][0][0]
    router_attack = first_scalars.get("AutomotiveNetwork.gateway.router.attackCount", 0)
    router_fast = first_scalars.get("AutomotiveNetwork.gateway.router.routingRatioFast", 0)

    if router_fast == 0:
        print(f"\n  [NOTE] All decisions routed to HEAVY path — STUB mode detected.")
        print(f"  Rebuild with real ONNX Runtime for actual detection results.")
    else:
        print(f"\n  [OK] Real ONNX inference mode active.")
        print(f"  Fast path ratio: {router_fast:.1%}")

    # Generate plots
    if HAS_PLOT:
        print(f"\nGenerating publication figures...")
        plot_results(all_configs, results_dir)
    else:
        print(f"\nInstall matplotlib+numpy for publication figures:")
        print(f"  pip install matplotlib numpy")


if __name__ == "__main__":
    main()
