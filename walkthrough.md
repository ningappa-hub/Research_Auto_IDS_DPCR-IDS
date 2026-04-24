# DPCR-IDS: Complete Reproduction Commands

> **Scope:** Every command needed to reproduce results from scratch — environment setup → data prep → training → evaluation → simulation → paper tables.

---

## Prerequisites

### Datasets (must be present before starting)

```
c:\ResearchAutoIDS\
├── datasets\
│   ├── Car-Hacking Dataset\         # CAN bus dataset
│   │   ├── DoS_dataset.csv
│   │   ├── Fuzzy_dataset.csv
│   │   ├── gear_dataset.csv
│   │   └── RPM_dataset.csv
│   └── tow-ids\                     # Ethernet (TOW-IDS) dataset
│       ├── pcap files ...
│       ├── y_train.csv
│       └── y_test.csv
```

### Software

- Python ≥ 3.10 with GPU (CUDA) support recommended
- OMNeT++ 6.x (via `opp_env`) for simulation
- ONNX Runtime 1.17+ (for real-inference simulation mode)

---

## Phase 0: Environment Setup

```powershell
# Navigate to project root
cd c:\ResearchAutoIDS

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate

# Install the project with ML dependencies (PyTorch, ONNX, scikit-learn, etc.)
pip install -e ".[ml]"

# Verify installation
dpcr-ids --help
```

**Expected output:** CLI help showing commands: `prepare-data`, `train-student`, `train-teacher`, `distill`, `calibrate`, `train-fallback`, `evaluate`, `export-onnx`, `serve-runtime`.

---

## Phase 1: Data Preparation

```powershell
# Prepare BOTH CAN and Ethernet datasets (temporal splits, feature extraction, z-score normalization)
dpcr-ids prepare-data --config configs/research_pipeline.yaml --protocol all
```

**Or prepare individually:**

```powershell
# CAN only
dpcr-ids prepare-data --config configs/research_pipeline.yaml --protocol can

# Ethernet only
dpcr-ids prepare-data --config configs/research_pipeline.yaml --protocol ethernet
```

**Artifacts created:**

```
artifacts/dpcr_ids_research_v1/prepared/
├── can/
│   ├── train.jsonl          # ~180K windows
│   ├── val.jsonl            # ~39K windows
│   ├── test.jsonl           # ~39K windows
│   ├── train.manifest.json
│   ├── val.manifest.json
│   ├── test.manifest.json
│   └── qa_report.json       # Contains z-score normalization params
└── ethernet/
    ├── train.jsonl
    ├── val.jsonl
    ├── test.jsonl
    ├── train.manifest.json
    ├── val.manifest.json
    ├── test.manifest.json
    └── qa_report.json
```

---

## Phase 2: Teacher Training

```powershell
# Train CAN teacher (Transformer architecture)
dpcr-ids train-teacher --config configs/research_pipeline.yaml --protocol can

# Train Ethernet teacher (Transformer architecture)
dpcr-ids train-teacher --config configs/research_pipeline.yaml --protocol ethernet
```

**Artifacts created:**

```
artifacts/dpcr_ids_research_v1/models/
├── can_teacher.pt           # CAN teacher checkpoint
├── can_teacher.json         # Training metrics
├── ethernet_teacher.pt      # ETH teacher checkpoint
└── ethernet_teacher.json    # Training metrics
```

---

## Phase 3: Student Training (Baseline)

```powershell
# Train CAN student (TCN architecture — depthwise separable temporal CNN)
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol can

# Train Ethernet student (CNN architecture — 2D conv on byte images)
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol ethernet
```

**Artifacts created:**

```
artifacts/dpcr_ids_research_v1/models/
├── can_student.pt           # CAN student checkpoint
├── can_student.json         # Training metrics
├── ethernet_student.pt      # ETH student checkpoint
└── ethernet_student.json    # Training metrics
```

---

## Phase 4: Knowledge Distillation

```powershell
# Distill CAN student from CAN teacher
dpcr-ids distill --config configs/research_pipeline.yaml --protocol can

# Distill Ethernet student from Ethernet teacher
dpcr-ids distill --config configs/research_pipeline.yaml --protocol ethernet
```

**Artifacts created:**

```
artifacts/dpcr_ids_research_v1/models/
├── can_student_distilled.pt           # Distilled CAN student
├── can_student_distilled.json
├── ethernet_student_distilled.pt      # Distilled ETH student
└── ethernet_student_distilled.json
```

---

## Phase 5: Temperature Calibration

```powershell
# Calibrate CAN student (fits temperature on validation logits)
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol can

# Calibrate Ethernet student
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol ethernet
```

**Artifacts created:**

```
artifacts/dpcr_ids_research_v1/calibration/
├── can.json               # {"temperature": 0.95, "ece_before": ..., "ece_after": ...}
└── ethernet.json          # {"temperature": 0.50, ...}
```

---

## Phase 6: Fallback Model Training

```powershell
# Train CAN fallback model (for uncertain routing decisions)
dpcr-ids train-fallback --config configs/research_pipeline.yaml --protocol can

# Train Ethernet fallback model
dpcr-ids train-fallback --config configs/research_pipeline.yaml --protocol ethernet
```

**Artifacts created:**

```
artifacts/dpcr_ids_research_v1/fallback/
├── can_fallback.json
└── ethernet_fallback.json
```

---

## Phase 7: Fusion Model Training

```powershell
# Train the late-fusion meta-model (uses frozen expert embeddings)
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol fusion

# Calibrate the fusion model
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol fusion
```

**Artifacts created:**

```
artifacts/dpcr_ids_research_v1/models/
├── fusion_student.pt          # Gated late-fusion head (9.7K params)
├── fusion_student.json
└── calibration/
    └── fusion.json
```

---

## Phase 8: Evaluation on Test Set

```powershell
# Evaluate CAN expert on test split
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol can

# Evaluate Ethernet expert on test split
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol ethernet

# Evaluate fusion system on test split
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol fusion
```

**Artifacts created:**

```
artifacts/dpcr_ids_research_v1/evaluations/
├── can_test_report.json
├── ethernet_test_report.json
└── fusion_test_report.json
```

---

## Phase 9: ONNX Export

### Standard ONNX Export (single-output — for offline validation)

```powershell
# Export CAN student to ONNX
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol can

# Export ETH student to ONNX
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol ethernet

# Export Fusion model to ONNX
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol fusion
```

### Dual-Output ONNX Export (for OMNeT++ simulation — logit + embedding)

```powershell
# Export CAN + ETH (dual-output) + Fusion into simulation models directory
python export_onnx_for_omnetpp.py --config configs/research_pipeline.yaml --output-dir dpcr-ids-sim/simulations/models
```

**Artifacts created:**

```
dpcr-ids-sim/simulations/models/
├── can_student.onnx           # Dual output: logit + 128-dim embedding
├── eth_student.onnx           # Dual output: logit + 128-dim embedding
├── fusion_student.onnx        # Single output: logit
└── can_normalization.json     # Z-score params for CAN feature normalization
```

---

## Phase 10: Runtime Replay Simulation (Python)

```powershell
# Full runtime replay — all protocols on test split
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test

# CAN only
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test --protocol can

# Ethernet only
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test --protocol ethernet

# Fusion only
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test --protocol fusion

# With sample limit (for quick validation)
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test --max-samples 1000
```

**Artifacts created:**

```
artifacts/dpcr_ids_research_v1/runtime_simulation/
└── test_real_model_replay.json    # Latency, routing, decision metrics
```

---

## Phase 11: OMNeT++ Simulation

> [!IMPORTANT]
> The OMNeT++ simulation runs on **Linux** inside the `opp_env` shell. The commands below assume you've transferred the project to a Linux environment with OMNeT++ 6.x installed via `opp_env`.

### 11a. Enter OMNeT++ Environment

```bash
# Start opp_env shell (Linux)
opp_env shell omnetpp-6.0.3
```

### 11b. Build Simulation — STUB Mode (No ONNX Runtime needed)

```bash
cd /c/ResearchAutoIDS/dpcr-ids-sim

# Build in stub mode (synthetic outputs, validates architecture)
bash build.sh
```

### 11c. Build Simulation — Real ONNX Inference Mode

```bash
cd /c/ResearchAutoIDS/dpcr-ids-sim

# Option 1: Automated setup + rebuild
bash setup_onnx_and_rebuild.sh

# Option 2: Manual steps
# Download ONNX Runtime
wget https://github.com/microsoft/onnxruntime/releases/download/v1.17.0/onnxruntime-linux-x64-1.17.0.tgz
tar xzf onnxruntime-linux-x64-1.17.0.tgz
export ONNX_RUNTIME_DIR=$(pwd)/onnxruntime-linux-x64-1.17.0
export LD_LIBRARY_PATH=$ONNX_RUNTIME_DIR/lib:$LD_LIBRARY_PATH

# Build with real ONNX
bash build.sh --with-onnx
```

### 11d. Run Individual Scenarios

```bash
# General (no attack — false-positive baseline)
bash run.sh General 30s

# Attack scenarios
bash run.sh DoS 20s
bash run.sh Fuzzy 20s
bash run.sh GearSpoof 20s
bash run.sh RpmSpoof 20s
bash run.sh MultiAttack 25s

# Bus load sweep
bash run.sh BusLoadLow 20s
bash run.sh BusLoadMed 20s
bash run.sh BusLoadHigh 20s

# ECU scaling sweep
bash run.sh ScaleSmall 20s
bash run.sh ScaleMedium 20s
bash run.sh ScaleLarge 20s
```

### 11e. Run ALL Scenarios (Batch)

```bash
# Runs all 12 scenarios × 5 repetitions = 60 simulation runs
bash run_all_scenarios.sh
```

**Artifacts created:**

```
dpcr-ids-sim/simulations/results/
├── General-0.sca .. General-4.sca       # Scalar results (5 reps each)
├── General-0.vec .. General-4.vec       # Vector results
├── DoS-0.sca .. DoS-4.sca
├── Fuzzy-0.sca .. Fuzzy-4.sca
├── GearSpoof-0.sca .. GearSpoof-4.sca
├── RpmSpoof-0.sca .. RpmSpoof-4.sca
├── MultiAttack-0.sca .. MultiAttack-4.sca
├── BusLoadLow-0.sca .. BusLoadHigh-4.sca
├── ScaleSmall-0.sca .. ScaleLarge-4.sca
├── ids_alerts_general.csv               # Alert CSVs
├── ids_alerts_dos.csv
├── ids_alerts_fuzzy.csv
├── ids_alerts_gear_spoof.csv
├── ids_alerts_rpm_spoof.csv
├── ids_alerts_multi.csv
├── ids_alerts_busload_*.csv
└── ids_alerts_scale_*.csv
```

---

## Phase 12: Analysis & Publication Artifacts

> [!NOTE]
> These commands run on **Windows** in the Python environment.

```powershell
# Activate environment
cd c:\ResearchAutoIDS
.venv\Scripts\activate

# 12a. Analyze simulation scalar/CSV results (text summary + optional plots)
python analyze_simulation_results.py --results-dir dpcr-ids-sim/simulations/results

# 12b. Generate all 7 publication figures
python plot_all_results.py

# 12c. Generate paper-ready tables (per-attack-type, complexity, distillation ablation)
python generate_paper_tables.py
```

**Artifacts created:**

```
dpcr-ids-sim/simulations/results/figures/
├── fig1_e2e_latency_attacks.png
├── fig2_traffic_volume.png
├── fig3_routing_decisions.png
├── fig4_alert_timelines.png
├── fig5_busload_impact.png
├── fig6_scaling_analysis.png
└── fig7_inference_breakdown.png

artifacts/dpcr_ids_research_v1/paper_tables/
├── paper_tables.md                      # Combined markdown report
├── can_per_attack_type.json
└── ethernet_per_attack_type.json
```

---

## Quick Reference: Full Pipeline in Order

```powershell
# ===== WINDOWS (Python) =====
cd c:\ResearchAutoIDS
.venv\Scripts\activate

# 1. Data
dpcr-ids prepare-data --config configs/research_pipeline.yaml --protocol all

# 2. Teachers
dpcr-ids train-teacher --config configs/research_pipeline.yaml --protocol can
dpcr-ids train-teacher --config configs/research_pipeline.yaml --protocol ethernet

# 3. Students (baseline)
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol can
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol ethernet

# 4. Distillation
dpcr-ids distill --config configs/research_pipeline.yaml --protocol can
dpcr-ids distill --config configs/research_pipeline.yaml --protocol ethernet

# 5. Calibration
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol can
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol ethernet

# 6. Fallback
dpcr-ids train-fallback --config configs/research_pipeline.yaml --protocol can
dpcr-ids train-fallback --config configs/research_pipeline.yaml --protocol ethernet

# 7. Fusion
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol fusion
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol fusion

# 8. Evaluate
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol can
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol ethernet
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol fusion

# 9. ONNX Export (for simulation)
python export_onnx_for_omnetpp.py --config configs/research_pipeline.yaml --output-dir dpcr-ids-sim/simulations/models

# 10. Runtime Replay
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test

# 11. Paper Tables
python generate_paper_tables.py
```

```bash
# ===== LINUX (opp_env — OMNeT++ Simulation) =====
opp_env shell omnetpp-6.0.3
cd /c/ResearchAutoIDS/dpcr-ids-sim

# Build with real ONNX
bash setup_onnx_and_rebuild.sh

# Run all 60 simulation runs
bash run_all_scenarios.sh
```

```powershell
# ===== BACK TO WINDOWS (Analysis) =====
cd c:\ResearchAutoIDS
.venv\Scripts\activate

# Analyze + plot
python analyze_simulation_results.py
python plot_all_results.py
```

---

## Config File Reference

| File | Purpose |
|------|---------|
| [research_pipeline.yaml](file:///c:/ResearchAutoIDS/configs/research_pipeline.yaml) | Master config: datasets, splits, model hyperparams, routing thresholds |
| [omnetpp.ini](file:///c:/ResearchAutoIDS/dpcr-ids-sim/simulations/omnetpp.ini) | OMNeT++ simulation parameters (12 scenario configs) |

## Key Hyperparameters (from config)

| Parameter | Value |
|-----------|-------|
| Seed | 42 |
| Train/Val/Test split | 70/15/15 |
| CAN window size | 100 frames |
| CAN stride | 50 frames |
| CAN features | 16 channels |
| ETH payload bytes | 1024 |
| ETH image size | 3 × 32 × 32 |
| Fusion bucket | 250ms |
| Batch size | 32 |
| Epochs | 50 (max) |
| Early stopping patience | 10 |
| Learning rate | 0.0002 |
| Distillation α | 0.5 |
| Distillation temperature | 4.0 |
| Router τ_low | 0.15 |
| Router τ_high | 0.85 |
| Simulation repetitions | 5 per config |
