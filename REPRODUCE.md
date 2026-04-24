# DPCR-IDS Complete Command Reference
## End-to-End Reproduction Guide — Every Command Used in This Research

---

> [!IMPORTANT]
> All commands below were used during the actual research work across multiple conversations. They are organized in the exact execution order needed to reproduce the full pipeline from scratch.

---

## Prerequisites

### Working Directory
All commands assume you are in the project root:
```
c:\ResearchAutoIDS
```

### Python Virtual Environment
```powershell
# Create virtual environment (one-time setup)
python -m venv .venv

# Activate (run this at the start of every session)
.venv\Scripts\activate
```

### Install the Package with ML Dependencies
```powershell
pip install -e ".[ml]"
```

This installs: `torch>=2.2`, `numpy>=1.24`, `pandas>=2.0`, `scapy>=2.5`, `scikit-learn>=1.3`, `onnx>=1.15`, `onnxruntime>=1.17`, `psutil>=5.9`, `pyyaml>=6.0`

### Additional Dependencies for Plotting
```powershell
pip install matplotlib
```

### Configuration File
All pipeline commands use:
```
configs/research_pipeline.yaml
```

---

## Phase 1: Data Preparation

### 1.1 Prepare All Datasets (CAN + Ethernet)
```powershell
dpcr-ids prepare-data --config configs/research_pipeline.yaml --protocol all
```

**What it does:**
- **CAN:** Reads 4 CSV files from `datasets/Car-Hacking Dataset/` (DoS, Fuzzy, Gear, RPM), extracts 16 features per frame, builds windows (size=100, stride=50), applies temporal split (70/15/15), fits z-score normalization on train only
- **Ethernet:** Reads TOW-IDS PCAPs + label CSVs from `datasets/tow-ids/`, converts payloads to 3-channel 32×32 byte-images, routes `y_train.csv` → train+val and `y_test.csv` → test
- **Output:** `artifacts/dpcr_ids_research_v1/prepared/can/` and `artifacts/dpcr_ids_research_v1/prepared/ethernet/` (train.jsonl, val.jsonl, test.jsonl + manifests)

### 1.2 Prepare Only CAN Data
```powershell
dpcr-ids prepare-data --config configs/research_pipeline.yaml --protocol can
```

### 1.3 Prepare Only Ethernet Data
```powershell
dpcr-ids prepare-data --config configs/research_pipeline.yaml --protocol ethernet
```

---

## Phase 2: Teacher Training

### 2.1 Train CAN Teacher (Transformer Encoder)
```powershell
dpcr-ids train-teacher --config configs/research_pipeline.yaml --protocol can
```

**What it does:**
- Trains `CanTeacherTransformer` (~795K params, d_model=128, nhead=8, layers=4)
- BCEWithLogitsLoss, AdamW (lr=0.0002, wd=1e-5), early stopping (patience=10)
- **Output:** `artifacts/dpcr_ids_research_v1/models/can_teacher.pt` + `can_teacher.json`

### 2.2 Train Ethernet Teacher (Vision Transformer)
```powershell
dpcr-ids train-teacher --config configs/research_pipeline.yaml --protocol ethernet
```

**What it does:**
- Trains `EthTeacherTransformer` (~799K params, patch-embed Conv2d(3→128, k=4, s=4))
- Same training config as CAN teacher
- **Output:** `artifacts/dpcr_ids_research_v1/models/ethernet_teacher.pt` + `ethernet_teacher.json`

> [!NOTE]
> The Ethernet teacher had convergence issues (best_epoch=1, early stopped). This is documented as a known limitation. The student trained independently still achieved excellent results.

---

## Phase 3: Student Training

### 3.1 Train CAN Student (TCN — Independent)
```powershell
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol can
```

**What it does:**
- Trains `CanStudentTCN` (22,977 params, 3 depthwise-separable blocks, dilations 1→2→4)
- Trained directly on ground-truth labels (BCEWithLogitsLoss)
- **Output:** `artifacts/dpcr_ids_research_v1/models/can_student.pt` + `can_student.json`

### 3.2 Train Ethernet Student (CNN — Independent)
```powershell
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol ethernet
```

**What it does:**
- Trains `EthStudentCNN` (28,033 params, 2-layer Conv2d→BN→ReLU→Pool)
- Trained directly on ground-truth labels
- **Output:** `artifacts/dpcr_ids_research_v1/models/ethernet_student.pt` + `ethernet_student.json`

---

## Phase 4: Knowledge Distillation

### 4.1 Distill CAN Student from CAN Teacher
```powershell
dpcr-ids distill --config configs/research_pipeline.yaml --protocol can
```

**What it does:**
- Loads trained CAN teacher, trains a new CAN student TCN using combined loss:
  `L = α × L_distill(student, teacher_soft, T=4.0) + (1-α) × L_BCE(student, hard_labels)` with α=0.5
- **Output:** `artifacts/dpcr_ids_research_v1/models/can_student_distilled.pt` + `can_student_distilled.json`

### 4.2 Distill Ethernet Student from Ethernet Teacher
```powershell
dpcr-ids distill --config configs/research_pipeline.yaml --protocol ethernet
```

**What it does:**
- Same distillation process for Ethernet
- **Output:** `artifacts/dpcr_ids_research_v1/models/ethernet_student_distilled.pt` + `ethernet_student_distilled.json`

---

## Phase 5: Temperature Calibration

### 5.1 Calibrate CAN Model
```powershell
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol can
```

**What it does:**
- Runs validation set through the best CAN model, fits optimal temperature via grid search (minimizes NLL)
- **Output:** `artifacts/dpcr_ids_research_v1/calibration/can.json` (contains: `temperature`, `ece_before`, `ece_after`)
- CAN calibrated temperature: **0.95**

### 5.2 Calibrate Ethernet Model
```powershell
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol ethernet
```

- Ethernet calibrated temperature: **0.50**

### 5.3 Calibrate Fusion Model
```powershell
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol fusion
```

- Fusion calibrated temperature: **1.10**

> [!NOTE]
> Calibration must be run AFTER training the corresponding model and BEFORE evaluation. The evaluate step automatically loads the calibration file if it exists and matches the model.

---

## Phase 6: Random Forest Fallback Training

### 6.1 Train CAN Fallback
```powershell
dpcr-ids train-fallback --config configs/research_pipeline.yaml --protocol can
```

**What it does:**
- Runs train+val through the CAN student, collects embeddings of **uncertain samples** (τ_low < p < τ_high, i.e., 0.15 < p < 0.85)
- Trains a Random Forest on those embeddings
- **Output:** `artifacts/dpcr_ids_research_v1/fallback/can_rf.pkl` + `can_rf.json`

### 6.2 Train Ethernet Fallback
```powershell
dpcr-ids train-fallback --config configs/research_pipeline.yaml --protocol ethernet
```

- **Output:** `artifacts/dpcr_ids_research_v1/fallback/ethernet_rf.pkl` + `ethernet_rf.json`

---

## Phase 7: Fusion Model Training

### 7.1 Train Fusion Head (Gated MLP)
```powershell
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol fusion
```

**What it does:**
- Automatically prepares fusion dataset: runs CAN + ETH students on their respective train/val splits, pairs outputs using pseudo-time alignment (250ms buckets)
- Trains `TinyLateFusionMetaModel` (1,459 params, gated expert projection + MLP)
- Input: `(batch, 2, 129)` — [logit + 128-d embedding] per expert
- **Output:** `artifacts/dpcr_ids_research_v1/models/fusion_student.pt` + `fusion_student.json`

> [!IMPORTANT]
> The fusion `train-student` command MUST be run AFTER both CAN and Ethernet students are trained, because it needs their checkpoints to generate the fusion dataset.

---

## Phase 8: Evaluation on Test Set

### 8.1 Evaluate CAN Student
```powershell
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol can
```

**What it does:**
- Loads best CAN model + calibration + fallback (if available)
- Runs full pipeline: model inference → calibration → confidence routing → fallback → decisions
- **Output:** `artifacts/dpcr_ids_research_v1/evaluations/can.json`
- Expected: F1=99.92%, DR=99.87%, FPR=0.031%, AUC-ROC=0.9999

### 8.2 Evaluate Ethernet Student
```powershell
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol ethernet
```

- **Output:** `artifacts/dpcr_ids_research_v1/evaluations/ethernet.json`
- Expected: Test F1=79.22% (due to CAN-DoS-Tunneled at 0% DR), Val F1=99.98%

### 8.3 Evaluate Fusion Model
```powershell
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol fusion
```

- **Output:** `artifacts/dpcr_ids_research_v1/evaluations/fusion.json`
- Expected: F1=94.76%, DR=93.06%, FPR=11.56%

---

## Phase 9: ONNX Export

### 9.1 Export Standard ONNX (Single-Output — Logit Only)
```powershell
# CAN Student ONNX
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol can

# Ethernet Student ONNX
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol ethernet

# Fusion Student ONNX
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol fusion
```

**Output:** `artifacts/dpcr_ids_research_v1/export/can_student.onnx`, `eth_student.onnx` (renamed from ethernet), `fusion_student.onnx`

### 9.2 Export Dual-Output ONNX for OMNeT++ (Logit + Embedding)
```powershell
python export_onnx_for_omnetpp.py --config configs/research_pipeline.yaml --output-dir dpcr-ids-sim/simulations/models
```

**What it does:**
- Exports CAN and ETH students with TWO outputs: `logits` (for classification) and `embedding` (128-d, for fusion pairing)
- Exports fusion model with single output (logit only)
- Verifies each export with ONNX Runtime
- **Output:**
  - `dpcr-ids-sim/simulations/models/can_student.onnx` (94.5 KB)
  - `dpcr-ids-sim/simulations/models/eth_student.onnx` (110.8 KB)
  - `dpcr-ids-sim/simulations/models/fusion_student.onnx` (7.3 KB)

---

## Phase 10: Runtime Simulation (Python — Full Pipeline Replay)

### 10.1 Run Full Runtime Simulation (All Protocols)
```powershell
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test
```

**What it does:**
- Replays prepared test splits through actual trained model checkpoints
- Full pipeline: inference → calibration → confidence routing → RF fallback → decision aggregation
- Measures per-sample inference latency, routing latency, end-to-end latency
- **Output:** `artifacts/dpcr_ids_research_v1/runtime_simulation/test_real_model_replay.json`

### 10.2 Run Single Protocol
```powershell
# CAN only
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test --protocol can

# Ethernet only
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test --protocol ethernet

# Fusion only
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test --protocol fusion
```

### 10.3 Quick Smoke Test (Limited Samples)
```powershell
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test --max-samples 100 --protocol can
```

---

## Phase 11: ONNX Benchmarking (Edge/Pi Validation)

### 11.1 Benchmark Fusion ONNX Model
```powershell
dpcr-ids-benchmark-fusion --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx --output-json artifacts/dpcr_ids_research_v1/export/fusion_benchmark.json --output-csv artifacts/dpcr_ids_research_v1/export/fusion_benchmark.csv --runs 5 --warmup-runs 100 --timed-runs 1000
```

**What it does:**
- Loads fusion ONNX via ONNX Runtime (CPU provider)
- Runs 5 benchmark rounds × 1000 timed inferences each (100 warmup per round)
- Reports p50/p95/p99 latency, peak RSS, CPU%
- **Output:** `fusion_benchmark.json` + `fusion_benchmark.csv`

### 11.2 Replay Fusion Test Set Through ONNX
```powershell
dpcr-ids-replay-fusion --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx --dataset artifacts/dpcr_ids_research_v1/prepared/fusion/test.jsonl --output-json artifacts/dpcr_ids_research_v1/export/fusion_replay.json --output-csv artifacts/dpcr_ids_research_v1/export/fusion_replay.csv --calibration-json artifacts/dpcr_ids_research_v1/calibration/fusion.json --baseline-report-json artifacts/dpcr_ids_research_v1/evaluations/fusion.json --predictions-jsonl artifacts/dpcr_ids_research_v1/export/fusion_predictions.jsonl
```

**What it does:**
- Feeds prepared fusion test samples through the ONNX model
- Applies temperature calibration
- Compares metrics against PyTorch baseline
- Outputs per-sample predictions with latency
- **Output:** `fusion_replay.json`, `fusion_replay.csv`, `fusion_predictions.jsonl`

---

## Phase 12: Publication Tables & Figures

### 12.1 Generate Paper-Ready Tables
```powershell
python generate_paper_tables.py
```

**What it does:**
- Per-attack-type detection rates (CAN + ETH) — runs inference on test.jsonl
- Model complexity summary (parameter counts, ONNX sizes, checkpoint sizes)
- Distillation ablation (teacher vs student vs distilled, from saved .json metadata)
- Simulation latency summary (from .sca files)
- **Output:** `artifacts/dpcr_ids_research_v1/paper_tables/paper_tables.md` + per-protocol JSON files

### 12.2 Analyze Simulation Results (Text + Basic Figures)
```powershell
python analyze_simulation_results.py --results-dir dpcr-ids-sim/simulations/results
```

**What it does:**
- Parses all .sca files and CSV alert logs from OMNeT++ simulation
- Prints per-scenario metric summaries and alert timeline analysis
- Generates 3 basic figures (E2E latency, routing decisions, alert timelines)
- **Output:** `dpcr-ids-sim/simulations/results/figures/`

### 12.3 Generate All 7+ Publication Figures
```powershell
python plot_all_results.py
```

**What it does:**
- Generates 7 comprehensive publication-quality figures:
  1. `fig1_e2e_latency_attacks.png` — E2E latency across attack scenarios
  2. `fig2_traffic_volume.png` — CAN frames and windows per scenario
  3. `fig3_routing_decisions.png` — Routing decision distribution (pie charts)
  4. `fig4_alert_timelines.png` — Alert timelines for all attack configs
  5. `fig5_busload_impact.png` — Bus load impact on latency
  6. `fig6_scaling_analysis.png` — ECU scaling analysis
  7. `fig7_inference_breakdown.png` — Pipeline latency breakdown
- **Output:** `dpcr-ids-sim/simulations/results/figures/`

---

## Phase 13: OMNeT++ Network Simulation (Linux/opp_env)

> [!WARNING]
> OMNeT++ simulation runs in a Linux environment via `opp_env`. These commands are executed inside the opp_env shell, NOT in Windows PowerShell.

### 13.1 Enter opp_env Shell
```bash
# On the Linux machine/WSL
opp_env shell omnetpp-6.3.0
```

### 13.2 Build Simulation (Stub Mode — No ONNX)
```bash
cd /c/ResearchAutoIDS/dpcr-ids-sim
bash ./build.sh
```

### 13.3 Build Simulation (Real ONNX Runtime)
```bash
cd /c/ResearchAutoIDS/dpcr-ids-sim
bash ./setup_onnx_and_rebuild.sh
```

**What it does:**
- Verifies ONNX Runtime 1.17.0 at `onnxruntime-linux-x64-1.17.0/`
- Sets `LD_LIBRARY_PATH` and `ONNX_RUNTIME_DIR`
- Runs `opp_makemake` with ONNX Runtime includes/libs
- Builds in release mode with `make -j$(nproc) MODE=release`
- Verifies ONNX model files exist in `simulations/models/`
- Runs a quick 5s smoke test on General config

### 13.4 Set LD_LIBRARY_PATH (Required Before Every Session)
```bash
export LD_LIBRARY_PATH=/c/ResearchAutoIDS/dpcr-ids-sim/onnxruntime-linux-x64-1.17.0/lib:$LD_LIBRARY_PATH
```

### 13.5 Run Individual Scenarios
```bash
cd /c/ResearchAutoIDS/dpcr-ids-sim

# Baseline (no attack)
bash ./run.sh General 30s

# Individual attack types
bash ./run.sh DoS 20s
bash ./run.sh Fuzzy 20s
bash ./run.sh GearSpoof 20s
bash ./run.sh RpmSpoof 20s

# Multi-attack (sequential DoS→Fuzzy→Spoof)
bash ./run.sh MultiAttack 25s

# Bus load sweep
bash ./run.sh BusLoadLow 20s
bash ./run.sh BusLoadMed 20s
bash ./run.sh BusLoadHigh 20s

# ECU scaling sweep
bash ./run.sh ScaleSmall 20s
bash ./run.sh ScaleMedium 20s
bash ./run.sh ScaleLarge 20s
```

### 13.6 Run ALL Scenarios (Batch — 12 Configurations)
```bash
cd /c/ResearchAutoIDS/dpcr-ids-sim
bash ./run_all_scenarios.sh
```

**What it does:**
- Runs all 12 simulation configurations sequentially
- Each config runs 5 repetitions (controlled by `repeat=5` in `omnetpp.ini`)
- Total: 60+ simulation runs
- **Output:** `simulations/results/*.sca`, `*.vec`, `*.csv`

### 13.7 Direct Execution (Alternative)
```bash
cd /c/ResearchAutoIDS/dpcr-ids-sim/simulations

/c/ResearchAutoIDS/dpcr-ids-sim/out/clang-release/src/dpcr-ids-sim \
    -u Cmdenv -n ../src -f omnetpp.ini \
    -c General --sim-time-limit=30s
```

---

## Phase 14: Unit Tests

### 14.1 Run All Tests
```powershell
python -m pytest tests/ -v
```

### 14.2 Run Specific Test Files
```powershell
# Data loading tests
python -m pytest tests/test_can_data.py -v
python -m pytest tests/test_ethernet_data.py -v

# Model tests
python -m pytest tests/test_late_fusion.py -v

# Training pipeline tests
python -m pytest tests/test_training_pipeline.py -v
python -m pytest tests/test_fusion_pipeline.py -v

# Metrics tests
python -m pytest tests/test_metrics.py -v

# Runtime tests
python -m pytest tests/test_router_runtime.py -v

# Export tests
python -m pytest tests/test_benchmark.py -v
python -m pytest tests/test_replay.py -v

# Config tests
python -m pytest tests/test_config.py -v
```

---

## Phase 15: Runtime Service (Interactive)

### 15.1 Check Runtime Service Status
```powershell
dpcr-ids serve-runtime --config configs/research_pipeline.yaml
```

### 15.2 Simulate a Single Event
```powershell
dpcr-ids serve-runtime --config configs/research_pipeline.yaml --protocol can --probability 0.95 --timestamp 1.0
```

---

## Phase 16: Git & Version Control

### 16.1 Initialize and Commit
```powershell
git init
git add .
git commit -m "Initial commit: DPCR-IDS research project"
```

### 16.2 Push to GitHub
```powershell
git remote add origin https://github.com/ningappa-hub/Research_Auto_IDS_DPCR-IDS.git
git branch -M main
git push -u origin main
```

---

## Quick Reference: Complete Pipeline (Copy-Paste Order)

```powershell
# ===== ACTIVATE ENVIRONMENT =====
.venv\Scripts\activate

# ===== PHASE 1: DATA =====
dpcr-ids prepare-data --config configs/research_pipeline.yaml --protocol all

# ===== PHASE 2: TEACHERS =====
dpcr-ids train-teacher --config configs/research_pipeline.yaml --protocol can
dpcr-ids train-teacher --config configs/research_pipeline.yaml --protocol ethernet

# ===== PHASE 3: STUDENTS =====
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol can
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol ethernet

# ===== PHASE 4: DISTILLATION =====
dpcr-ids distill --config configs/research_pipeline.yaml --protocol can
dpcr-ids distill --config configs/research_pipeline.yaml --protocol ethernet

# ===== PHASE 5: CALIBRATION =====
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol can
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol ethernet

# ===== PHASE 6: FALLBACK =====
dpcr-ids train-fallback --config configs/research_pipeline.yaml --protocol can
dpcr-ids train-fallback --config configs/research_pipeline.yaml --protocol ethernet

# ===== PHASE 7: FUSION =====
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol fusion
dpcr-ids calibrate --config configs/research_pipeline.yaml --protocol fusion

# ===== PHASE 8: EVALUATION =====
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol can
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol ethernet
dpcr-ids evaluate --config configs/research_pipeline.yaml --protocol fusion

# ===== PHASE 9: ONNX EXPORT =====
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol can
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol ethernet
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol fusion
python export_onnx_for_omnetpp.py --config configs/research_pipeline.yaml

# ===== PHASE 10: RUNTIME SIMULATION =====
python simulate_real_model_runtime.py --config configs/research_pipeline.yaml --split test

# ===== PHASE 11: BENCHMARKING =====
dpcr-ids-benchmark-fusion --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx --output-json artifacts/dpcr_ids_research_v1/export/fusion_benchmark.json --runs 5 --warmup-runs 100 --timed-runs 1000
dpcr-ids-replay-fusion --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx --dataset artifacts/dpcr_ids_research_v1/prepared/fusion/test.jsonl --output-json artifacts/dpcr_ids_research_v1/export/fusion_replay.json --calibration-json artifacts/dpcr_ids_research_v1/calibration/fusion.json --baseline-report-json artifacts/dpcr_ids_research_v1/evaluations/fusion.json

# ===== PHASE 12: PAPER TABLES & FIGURES =====
python generate_paper_tables.py
python plot_all_results.py

# ===== PHASE 13: OMNeT++ (Linux/opp_env) =====
# opp_env shell omnetpp-6.3.0
# cd /c/ResearchAutoIDS/dpcr-ids-sim
# bash ./setup_onnx_and_rebuild.sh
# bash ./run_all_scenarios.sh

# ===== PHASE 14: ANALYSIS (back on Windows) =====
python analyze_simulation_results.py --results-dir dpcr-ids-sim/simulations/results

# ===== PHASE 15: TESTS =====
python -m pytest tests/ -v
```

---

## Output Artifacts Summary

| Phase | Key Output Files |
|---|---|
| Data Prep | `artifacts/.../prepared/{can,ethernet}/{train,val,test}.jsonl` |
| Teachers | `artifacts/.../models/{can,ethernet}_teacher.pt` |
| Students | `artifacts/.../models/{can,ethernet}_student.pt` |
| Distilled | `artifacts/.../models/{can,ethernet}_student_distilled.pt` |
| Calibration | `artifacts/.../calibration/{can,ethernet,fusion}.json` |
| Fallback | `artifacts/.../fallback/{can,ethernet}_rf.pkl` |
| Fusion | `artifacts/.../models/fusion_student.pt` |
| Evaluation | `artifacts/.../evaluations/{can,ethernet,fusion}.json` |
| ONNX Export | `artifacts/.../export/{can,eth,fusion}_student.onnx` |
| Dual ONNX | `dpcr-ids-sim/simulations/models/*.onnx` |
| Runtime Sim | `artifacts/.../runtime_simulation/test_real_model_replay.json` |
| Benchmark | `artifacts/.../export/fusion_benchmark.json` |
| Replay | `artifacts/.../export/fusion_replay.json` |
| Paper Tables | `artifacts/.../paper_tables/paper_tables.md` |
| OMNeT++ | `dpcr-ids-sim/simulations/results/*.sca, *.csv` |
| Figures | `dpcr-ids-sim/simulations/results/figures/*.png` |
