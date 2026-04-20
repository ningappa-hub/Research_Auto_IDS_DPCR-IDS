# Raspberry Pi Deployment And Validation Guide

This guide deploys the corrected fusion ONNX model to a Raspberry Pi and validates it in two modes:

1. `Benchmark`: measure latency, RAM, CPU, and model footprint.
2. `Replay`: feed prepared fusion tensors from `prepared/fusion/test.jsonl` through ONNX Runtime and compare with the desktop baseline.

## Current Scope

What works today:
- `fusion_student.onnx` CPU inference on Raspberry Pi
- `dpcr-ids-benchmark-fusion` for edge latency/RAM benchmarking
- `dpcr-ids-replay-fusion` for replaying prepared fusion tensors and producing Pi-side metrics
- `dpcr-ids serve-runtime` to simulate routing and aggregation behavior

What is not implemented yet:
- live `SocketCAN` capture to expert windows on the Pi
- live Automotive Ethernet capture to expert tensors on the Pi
- ONNX export for CAN/Ethernet experts with both `logit + 128-d embedding`
- end-to-end raw `CAN + AutoEth -> [2,129] -> fusion ONNX` on the Pi

## 1. Hardware And OS

Recommended baseline:
- Raspberry Pi 5
- 64-bit Raspberry Pi OS
- Ethernet or Wi-Fi network access
- SSH enabled during imaging

Optional monitoring commands on the Pi:
```bash
vcgencmd measure_temp
vcgencmd get_throttled
free -h
```

## 2. First Connection From Windows

From Windows PowerShell:
```powershell
ssh <pi_user>@<pi_hostname>.local
```

Verify architecture on the Pi:
```bash
uname -m
```

Expected:
```text
aarch64
```

## 3. Prepare The Pi

On the Pi:
```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y python3 python3-venv python3-pip git rsync jq htop

mkdir -p ~/ResearchAutoIDS
cd ~/ResearchAutoIDS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy onnxruntime psutil
```

## 4. Copy Minimum Files From Windows

Run from `C:\ResearchAutoIDS` in Windows PowerShell:
```powershell
ssh <pi_user>@<pi_hostname>.local "mkdir -p ~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/export ~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/prepared/fusion ~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/evaluations ~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/calibration ~/ResearchAutoIDS/configs"

scp pyproject.toml <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/
scp -r src <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/
scp configs/research_pipeline.yaml <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/configs/
scp artifacts/dpcr_ids_research_v1/export/fusion_student.onnx <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/export/
scp artifacts/dpcr_ids_research_v1/prepared/fusion/test.jsonl <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/prepared/fusion/
scp artifacts/dpcr_ids_research_v1/evaluations/fusion.json <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/evaluations/
scp artifacts/dpcr_ids_research_v1/calibration/fusion.json <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/calibration/
```

## 5. Install The Local Package On Pi

On the Pi:
```bash
cd ~/ResearchAutoIDS
source .venv/bin/activate
python -m pip install -e .
export PYTHONPATH=$PWD/src
```

## 6. Sanity Check The ONNX Model

On the Pi:
```bash
python - <<'PY'
import onnxruntime as ort
session = ort.InferenceSession(
    "artifacts/dpcr_ids_research_v1/export/fusion_student.onnx",
    providers=["CPUExecutionProvider"],
)
print("Input:", session.get_inputs()[0].shape)
print("Output:", session.get_outputs()[0].shape)
PY
```

Expected input shape:
```text
[None, 2, 129]
```

## 7. Benchmark The Fusion ONNX Model

On the Pi:
```bash
dpcr-ids-benchmark-fusion \
  --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx \
  --output-json artifacts/dpcr_ids_research_v1/export/fusion_benchmark_pi.json \
  --output-csv artifacts/dpcr_ids_research_v1/export/fusion_benchmark_pi.csv \
  --warmup-runs 100 \
  --timed-runs 1000
```

This reports:
- `onnx_size_mb`
- `latency_ms_p50`
- `latency_ms_p95`
- `latency_ms_p99`
- `latency_ms_mean`
- `latency_ms_std`
- `rss_mb_peak`
- `cpu_percent_mean`

## 8. Replay Prepared Fusion Traffic On Pi

This is the current supported way to feed traffic-like inputs to the fusion model.

On the Pi:
```bash
dpcr-ids-replay-fusion \
  --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx \
  --dataset artifacts/dpcr_ids_research_v1/prepared/fusion/test.jsonl \
  --calibration-json artifacts/dpcr_ids_research_v1/calibration/fusion.json \
  --baseline-report-json artifacts/dpcr_ids_research_v1/evaluations/fusion.json \
  --output-json artifacts/dpcr_ids_research_v1/export/fusion_replay_pi.json \
  --output-csv artifacts/dpcr_ids_research_v1/export/fusion_replay_pi.csv \
  --predictions-jsonl artifacts/dpcr_ids_research_v1/export/fusion_replay_predictions_pi.jsonl \
  --batch-size 1
```

The replay report includes:
- Pi-side classification metrics: `precision`, `recall`, `f1`, `fpr`, `ece`
- replay latency distribution: `p50/p95/p99/mean/std`
- peak RSS and mean CPU
- `baseline_comparison` vs the desktop `fusion.json`

Expected research use:
- show that Pi replay metrics closely match desktop replay metrics
- show that single-sample CPU latency fits the gateway budget

## 9. Simulate Runtime Routing

This is separate from model replay. It validates runtime routing and fail-open logic.

On the Pi:
```bash
dpcr-ids serve-runtime --config configs/research_pipeline.yaml --protocol can --probability 0.92
dpcr-ids serve-runtime --config configs/research_pipeline.yaml --protocol ethernet --probability 0.18
```

## 10. Collect Results Back To Windows

From Windows PowerShell:
```powershell
scp <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/export/fusion_benchmark_pi.json artifacts/dpcr_ids_research_v1/export/
scp <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/export/fusion_benchmark_pi.csv artifacts/dpcr_ids_research_v1/export/
scp <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/export/fusion_replay_pi.json artifacts/dpcr_ids_research_v1/export/
scp <pi_user>@<pi_hostname>.local:~/ResearchAutoIDS/artifacts/dpcr_ids_research_v1/export/fusion_replay_pi.csv artifacts/dpcr_ids_research_v1/export/
```

## 11. Metrics To Report In The Paper

### Edge-resource metrics
- `onnx_size_mb`
- `latency_ms_p50`
- `latency_ms_p95`
- `latency_ms_p99`
- `latency_ms_mean ± latency_ms_std`
- `rss_mb_peak`
- `cpu_percent_mean`
- temperature and throttling observations

### Detection parity metrics
- `precision`
- `recall`
- `f1`
- `fpr`
- `ece`
- desktop vs Pi delta for the same `test.jsonl`

### Recommended tables
- Table 1: `Model`, `Input`, `ONNX size`, `Platform`
- Table 2: `Batch`, `p50`, `p95`, `p99`, `Mean ± Std`, `Peak RSS`, `CPU mean`
- Table 3: `Desktop replay vs Pi replay`: `F1`, `Recall`, `Precision`, `FPR`, `ECE`

## 12. What “Traffic Feeding” Means Right Now

Current valid feed path:
- prepared fusion samples from `artifacts/dpcr_ids_research_v1/prepared/fusion/test.jsonl`
- each row already contains the `float32 [2,129]` tensor expected by the fusion model

This is enough to prove:
- deployment works
- ONNX inference works on Pi CPU
- replay accuracy and latency are stable

It does not yet prove:
- live CAN and live Automotive Ethernet ingestion on Pi
- real-time expert feature construction on Pi
- full raw bus capture to fusion inference

## 13. Live Bench Roadmap After Pi Replay

### CAN bench
Required hardware:
- Raspberry Pi + USB-CAN FD adapter
- `can-utils`
- `SocketCAN` interface such as `can0`

Typical traffic tools:
```bash
sudo apt install -y can-utils
sudo ip link set can0 up type can bitrate 500000
candump can0
cangen can0
canplayer -I trace.log
```

### Automotive Ethernet bench
Required hardware:
- Pi `eth0` for mirrored RJ45 replay, or
- T1 media converter / tap for real Automotive Ethernet
- replay tool such as `tcpreplay`

### Additional code needed before full live fusion
One of these must be added:
- export CAN/Ethernet experts with dual outputs `(logit, embedding)` to ONNX, or
- run the expert models on the Pi in PyTorch and keep only the fusion head in ONNX

Then add a live capture bridge that:
- builds CAN windows `(16,100)`
- builds Ethernet tensors `(3,32,32)`
- computes expert tokens `[logit; embedding]`
- stacks them into `[2,129]`
- feeds `fusion_student.onnx`
