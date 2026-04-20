"""
plot_all_results.py — Generate comprehensive publication figures for DPCR-IDS.
"""
import csv, os, re
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.size': 11,
    'axes.titlesize': 13, 'axes.labelsize': 12,
    'figure.dpi': 150, 'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15
})

RESULTS = 'dpcr-ids-sim/simulations/results'
FIGURES = os.path.join(RESULTS, 'figures')
os.makedirs(FIGURES, exist_ok=True)

# --- Parsers ---
def parse_sca(fp):
    s = {}
    with open(fp) as f:
        for l in f:
            if l.startswith('scalar '):
                p = l.strip().split(None, 3)
                if len(p) >= 4:
                    try: s[f"{p[1]}.{p[2]}"] = float(p[3])
                    except: pass
    return s

def parse_csv(fp):
    if not os.path.exists(fp): return []
    with open(fp) as f:
        return [{'simtime': float(r['simtime']), 'decision': r['decision'],
                 'p_attack_calibrated': float(r['p_attack_calibrated']),
                 'latency_ms': float(r['latency_ms']),
                 'escalate': r['escalate']=='true'} for r in csv.DictReader(f)]

def find_configs():
    configs = defaultdict(list)
    for f in sorted(os.listdir(RESULTS)):
        m = re.match(r'^(.+)-(\d+)\.sca$', f)
        if m: configs[m.group(1)].append(parse_sca(os.path.join(RESULTS, f)))
    return dict(configs)

def avg(scalars_list, key):
    vals = [s.get(key, 0) for s in scalars_list]
    vals = [v for v in vals if isinstance(v, (int, float))]
    return np.mean(vals) if vals else 0

def std(scalars_list, key):
    vals = [s.get(key, 0) for s in scalars_list]
    vals = [v for v in vals if isinstance(v, (int, float))]
    return np.std(vals) if len(vals) > 1 else 0

# --- Load all data ---
configs = find_configs()
print(f"Found {len(configs)} configs: {', '.join(sorted(configs.keys()))}")

CSV_MAP = {'General':'ids_alerts_general.csv','DoS':'ids_alerts_dos.csv',
           'Fuzzy':'ids_alerts_fuzzy.csv','GearSpoof':'ids_alerts_gear_spoof.csv',
           'RpmSpoof':'ids_alerts_rpm_spoof.csv','MultiAttack':'ids_alerts_multi.csv',
           'BusLoadLow':'ids_alerts_busload_low.csv','BusLoadMed':'ids_alerts_busload_med.csv',
           'BusLoadHigh':'ids_alerts_busload_high.csv','ScaleSmall':'ids_alerts_scale_small.csv',
           'ScaleMedium':'ids_alerts_scale_med.csv','ScaleLarge':'ids_alerts_scale_large.csv'}

alerts = {k: parse_csv(os.path.join(RESULTS, CSV_MAP.get(k, ''))) for k in configs}

# ===== FIGURE 1: E2E Latency Across All Configs =====
print("Generating Figure 1: E2E Latency...")
attack_configs = ['General','DoS','Fuzzy','GearSpoof','RpmSpoof','MultiAttack']
attack_present = [c for c in attack_configs if c in configs]

fig, ax = plt.subplots(figsize=(12, 5))
x = np.arange(len(attack_present))
mean_lat = [avg(configs[c], 'AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:mean') for c in attack_present]
max_lat = [avg(configs[c], 'AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:max') for c in attack_present]
std_lat = [std(configs[c], 'AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:mean') for c in attack_present]

bars1 = ax.bar(x - 0.2, mean_lat, 0.35, yerr=std_lat, label='Mean E2E Latency',
               color='#1976D2', capsize=4, edgecolor='white')
bars2 = ax.bar(x + 0.2, max_lat, 0.35, label='Max E2E Latency',
               color='#E64A19', edgecolor='white')
ax.set_xlabel('Scenario')
ax.set_ylabel('End-to-End Latency (ms)')
ax.set_title('DPCR-IDS End-to-End Detection Latency by Attack Scenario')
ax.set_xticks(x)
ax.set_xticklabels(attack_present, rotation=30, ha='right')
ax.legend()
ax.grid(axis='y', alpha=0.3)
fig.savefig(os.path.join(FIGURES, 'fig1_e2e_latency_attacks.png'))
plt.close()
print("  -> fig1_e2e_latency_attacks.png")

# ===== FIGURE 2: CAN Frames & Windows per Scenario =====
print("Generating Figure 2: Traffic Volume...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

can_frames = [avg(configs[c], 'AutomotiveNetwork.gateway.canExpert.framesReceived') for c in attack_present]
can_windows = [avg(configs[c], 'AutomotiveNetwork.gateway.canExpert.windowsProcessed') for c in attack_present]

colors = ['#4CAF50','#F44336','#FF9800','#9C27B0','#00BCD4','#795548']
ax1.bar(attack_present, can_frames, color=colors[:len(attack_present)], edgecolor='white')
ax1.set_ylabel('CAN Frames Received')
ax1.set_title('CAN Traffic Volume by Scenario')
ax1.tick_params(axis='x', rotation=30)
for i, v in enumerate(can_frames):
    ax1.text(i, v + max(can_frames)*0.02, f'{v/1000:.0f}K', ha='center', fontsize=9)

ax2.bar(attack_present, can_windows, color=colors[:len(attack_present)], edgecolor='white')
ax2.set_ylabel('CAN Windows Processed')
ax2.set_title('IDS Processing Load by Scenario')
ax2.tick_params(axis='x', rotation=30)
for i, v in enumerate(can_windows):
    ax2.text(i, v + max(can_windows)*0.02, f'{v:.0f}', ha='center', fontsize=9)

fig.suptitle('DPCR-IDS Traffic Volume Impact', fontsize=14, y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(FIGURES, 'fig2_traffic_volume.png'))
plt.close()
print("  -> fig2_traffic_volume.png")

# ===== FIGURE 3: Routing Decision Distribution =====
print("Generating Figure 3: Routing Decisions...")
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes_flat = axes.flatten()

for idx, cfg in enumerate(attack_present):
    ax = axes_flat[idx]
    s = configs[cfg][0]
    normal = s.get('AutomotiveNetwork.gateway.router.normalCount', 0)
    attack = s.get('AutomotiveNetwork.gateway.router.attackCount', 0)
    escalate = s.get('AutomotiveNetwork.gateway.router.escalateCount', 0)

    vals = [normal, attack, escalate]
    labels = ['NORMAL', 'ATTACK', 'ESCALATE']
    clrs = ['#4CAF50', '#F44336', '#FF9800']
    filtered = [(l,v,c) for l,v,c in zip(labels, vals, clrs) if v > 0]
    if filtered:
        fl, fv, fc = zip(*filtered)
        wedges, texts, autotexts = ax.pie(fv, labels=fl, colors=fc,
            autopct='%1.1f%%', startangle=90, textprops={'fontsize':9})
    ax.set_title(cfg, fontsize=12, fontweight='bold')

fig.suptitle('Confidence Router Decision Distribution', fontsize=14)
fig.tight_layout()
fig.savefig(os.path.join(FIGURES, 'fig3_routing_decisions.png'))
plt.close()
print("  -> fig3_routing_decisions.png")

# ===== FIGURE 4: Alert Timelines for All Attacks =====
print("Generating Figure 4: Alert Timelines...")
timeline_configs = [c for c in attack_present if len(alerts.get(c, [])) > 3]
n_plots = len(timeline_configs)
if n_plots > 0:
    fig, axes = plt.subplots(n_plots, 1, figsize=(14, 3.5*n_plots), sharex=False)
    if n_plots == 1: axes = [axes]

    color_map = {'NORMAL':'#4CAF50', 'ATTACK':'#F44336', 'ESCALATE':'#FF9800'}
    for idx, cfg in enumerate(timeline_configs):
        ax = axes[idx]
        a = alerts[cfg]
        times = [x['simtime'] for x in a]
        probs = [x['p_attack_calibrated'] for x in a]
        c = [color_map.get(x['decision'], '#999') for x in a]

        ax.scatter(times, probs, c=c, s=40, alpha=0.85, edgecolors='black', linewidths=0.5, zorder=3)
        ax.axhline(y=0.85, color='red', linestyle='--', alpha=0.4, linewidth=1)
        ax.axhline(y=0.15, color='green', linestyle='--', alpha=0.4, linewidth=1)
        ax.axhline(y=0.30, color='orange', linestyle=':', alpha=0.3, linewidth=1)

        # Mark attack window
        if cfg == 'DoS':
            ax.axvspan(5, 15, alpha=0.08, color='red', label='Attack Window')
        elif cfg in ('Fuzzy','GearSpoof','RpmSpoof'):
            ax.axvspan(5, 15, alpha=0.08, color='red', label='Attack Window')
        elif cfg == 'MultiAttack':
            ax.axvspan(3, 8, alpha=0.06, color='red')
            ax.axvspan(8, 13, alpha=0.06, color='orange')
            ax.axvspan(14, 19, alpha=0.06, color='purple')

        ax.set_ylabel('P(attack)')
        ax.set_title(f'{cfg} — Alert Timeline', fontweight='bold')
        ax.set_ylim(-0.05, 1.05)
        ax.grid(alpha=0.2)

    axes[-1].set_xlabel('Simulation Time (s)')

    patches = [mpatches.Patch(color='#4CAF50', label='NORMAL'),
               mpatches.Patch(color='#F44336', label='ATTACK'),
               mpatches.Patch(color='#FF9800', label='ESCALATE')]
    fig.legend(handles=patches, loc='upper right', fontsize=10)
    fig.suptitle('DPCR-IDS Alert Timelines Across Attack Scenarios', fontsize=14, y=1.01)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, 'fig4_alert_timelines.png'))
    plt.close()
    print("  -> fig4_alert_timelines.png")

# ===== FIGURE 5: Bus Load Impact =====
print("Generating Figure 5: Bus Load Impact...")
busload_configs = ['BusLoadLow','BusLoadMed','BusLoadHigh']
busload_present = [c for c in busload_configs if c in configs]
if busload_present:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    bus_labels = ['Low (2 ECUs)','Medium (8 ECUs)','High (15 ECUs)'][:len(busload_present)]

    lat_mean = [avg(configs[c], 'AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:mean') for c in busload_present]
    lat_max = [avg(configs[c], 'AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:max') for c in busload_present]
    lat_std = [std(configs[c], 'AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:mean') for c in busload_present]

    ax1.errorbar(bus_labels, lat_mean, yerr=lat_std, fmt='o-', color='#1976D2',
                 linewidth=2, markersize=8, capsize=5, label='Mean E2E')
    ax1.plot(bus_labels, lat_max, 's--', color='#E64A19', linewidth=2, markersize=8, label='Max E2E')
    ax1.set_ylabel('Latency (ms)')
    ax1.set_title('Detection Latency vs Bus Load')
    ax1.legend()
    ax1.grid(alpha=0.3)

    can_rx = [avg(configs[c], 'AutomotiveNetwork.gateway.canExpert.framesReceived') for c in busload_present]
    windows = [avg(configs[c], 'AutomotiveNetwork.gateway.canExpert.windowsProcessed') for c in busload_present]
    inf_ms = [avg(configs[c], 'AutomotiveNetwork.gateway.canExpert.canInferenceMs:mean') for c in busload_present]

    ax2.bar(bus_labels, can_rx, color=['#81C784','#FFB74D','#E57373'], edgecolor='white')
    ax2.set_ylabel('CAN Frames Received')
    ax2.set_title('CAN Traffic vs Bus Load')
    for i, v in enumerate(can_rx):
        ax2.text(i, v + max(can_rx)*0.02, f'{v/1000:.0f}K', ha='center', fontsize=9)

    fig.suptitle('Impact of CAN Bus Load on IDS Performance', fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, 'fig5_busload_impact.png'))
    plt.close()
    print("  -> fig5_busload_impact.png")

# ===== FIGURE 6: ECU Scaling =====
print("Generating Figure 6: ECU Scaling...")
scale_configs = ['ScaleSmall','ScaleMedium','ScaleLarge']
scale_present = [c for c in scale_configs if c in configs]
if scale_present:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    scale_labels = ['5 ECUs','10 ECUs','20 ECUs'][:len(scale_present)]

    lat_mean = [avg(configs[c], 'AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:mean') for c in scale_present]
    windows = [avg(configs[c], 'AutomotiveNetwork.gateway.canExpert.windowsProcessed') for c in scale_present]
    gw_alerts = [avg(configs[c], 'AutomotiveNetwork.gateway.aggregator.totalFlushed') for c in scale_present]
    fusion = [avg(configs[c], 'AutomotiveNetwork.gateway.fusion.fusionsPaired') for c in scale_present]

    x = np.arange(len(scale_present))
    ax1.bar(x-0.2, windows, 0.35, label='CAN Windows', color='#42A5F5', edgecolor='white')
    ax1.bar(x+0.2, fusion, 0.35, label='Fusion Pairings', color='#AB47BC', edgecolor='white')
    ax1.set_xticks(x)
    ax1.set_xticklabels(scale_labels)
    ax1.set_ylabel('Count')
    ax1.set_title('Processing Volume vs Network Scale')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    ax2.plot(scale_labels, lat_mean, 'o-', color='#1976D2', linewidth=2, markersize=10)
    ax2.set_ylabel('Mean E2E Latency (ms)')
    ax2.set_title('Detection Latency vs Network Scale')
    ax2.grid(alpha=0.3)
    for i, v in enumerate(lat_mean):
        ax2.annotate(f'{v:.1f}ms', (i, v), textcoords='offset points',
                     xytext=(0, 12), ha='center', fontsize=10)

    fig.suptitle('DPCR-IDS Scalability Analysis', fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, 'fig6_scaling_analysis.png'))
    plt.close()
    print("  -> fig6_scaling_analysis.png")

# ===== FIGURE 7: Inference Latency Breakdown =====
print("Generating Figure 7: Inference Breakdown...")
fig, ax = plt.subplots(figsize=(12, 5))
all_cfgs = sorted(configs.keys())

can_inf = [avg(configs[c], 'AutomotiveNetwork.gateway.canExpert.canInferenceMs:mean') for c in all_cfgs]
eth_inf = [avg(configs[c], 'AutomotiveNetwork.gateway.ethExpert.ethInferenceMs:mean') for c in all_cfgs]
fus_inf = [avg(configs[c], 'AutomotiveNetwork.gateway.fusion.fusionInferenceMs:mean') for c in all_cfgs]
rout_lat = [avg(configs[c], 'AutomotiveNetwork.gateway.router.routingLatencyMs:mean') for c in all_cfgs]

x = np.arange(len(all_cfgs))
w = 0.6
b1 = ax.bar(x, can_inf, w, label='CAN Expert', color='#E53935')
b2 = ax.bar(x, eth_inf, w, bottom=can_inf, label='ETH Expert', color='#1E88E5')
b3 = ax.bar(x, fus_inf, w, bottom=np.array(can_inf)+np.array(eth_inf), label='Fusion', color='#43A047')
b4 = ax.bar(x, rout_lat, w, bottom=np.array(can_inf)+np.array(eth_inf)+np.array(fus_inf),
            label='Router', color='#FB8C00')

ax.set_xlabel('Configuration')
ax.set_ylabel('Inference Latency (ms)')
ax.set_title('DPCR-IDS Pipeline Latency Breakdown (per-window)')
ax.set_xticks(x)
ax.set_xticklabels(all_cfgs, rotation=45, ha='right', fontsize=9)
ax.legend(loc='upper right')
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIGURES, 'fig7_inference_breakdown.png'))
plt.close()
print("  -> fig7_inference_breakdown.png")

# ===== SUMMARY TABLE =====
print("\n" + "="*80)
print("  COMPLETE RESULTS SUMMARY")
print("="*80)
print(f"{'Config':<16} {'CAN Frames':>12} {'Windows':>10} {'Fusion':>8} {'NORMAL':>8} {'ATTACK':>8} {'ESCAL':>8} {'E2E(ms)':>10} {'Alerts':>8}")
print("-"*80)
for cfg in sorted(configs.keys()):
    s = configs[cfg]
    print(f"{cfg:<16} {avg(s,'AutomotiveNetwork.gateway.canExpert.framesReceived'):>12.0f} "
          f"{avg(s,'AutomotiveNetwork.gateway.canExpert.windowsProcessed'):>10.0f} "
          f"{avg(s,'AutomotiveNetwork.gateway.fusion.fusionsPaired'):>8.0f} "
          f"{avg(s,'AutomotiveNetwork.gateway.router.normalCount'):>8.0f} "
          f"{avg(s,'AutomotiveNetwork.gateway.router.attackCount'):>8.0f} "
          f"{avg(s,'AutomotiveNetwork.gateway.router.escalateCount'):>8.0f} "
          f"{avg(s,'AutomotiveNetwork.gateway.aggregator.endToEndLatencyMs:mean'):>10.1f} "
          f"{avg(s,'AutomotiveNetwork.gateway.aggregator.totalFlushed'):>8.0f}")

print(f"\n7 figures saved to: {FIGURES}/")
print("Done!")
