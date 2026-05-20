# DPCR-IDS: Dual-Protocol Cascade Routing Intrusion Detection System

Research-first implementation scaffold for a calibrated late-fusion dual-protocol IDS covering CAN and automotive Ethernet. 

This repository implements a lightweight, dual-protocol intrusion detection system designed to run on resource-constrained automotive gateway hardware. It covers both CAN Bus and Automotive Ethernet through a two-tier cascade architecture featuring late decision fusion and confidence-based routing.

## 📌 Recent Updates

1. **Expert-Aware Router Override:** The router now short-circuits to NORMAL when ALL experts independently predict high-confidence normal. This completely fixes the fusion false-positive rate in baseline scenarios.
2. **Data Memorization & Overfitting Fixes:** Addressed severe overfitting by implementing Dropout in CNN architectures, class-balanced weighting (`pos_weight`), and transitioning to AUC-PR early-stopping. 
3. **Per-Attack-Type Evaluation:** Granular evaluation now breaks down detection rates by specific attack types.
4. **Real ONNX Runtime Integration:** The OMNeT++ simulation now utilizes real trained ONNX models via the ONNX Runtime 1.17.0 C++ library.
5. **Three-tier Fallback Cascade:** Implemented a new Random Forest fallback classifier for uncertain samples before triggering the heavy-path fusion model.

## 📊 Performance Metrics

### CAN Student Performance (Test Set)
The CAN model utilizes a depthwise-separable Temporal CNN structure (22,977 parameters).
* **F1-Score:** 99.98%
* **Detection Rate (Recall):** 99.97%
* **False Positive Rate:** 0.01%
* **Per-Attack Detection Rate:** DoS (99.94%), Fuzzy (99.97%), Gear Spoofing (99.96%), RPM Spoofing (100.0%)

### Ethernet Student Performance (Test Set)
The Ethernet model utilizes a lightweight 2D CNN architecture (28,033 parameters).
* **Overall F1-Score:** 79.22%
* **Overall Detection Rate:** 68.31%
* **False Positive Rate:** 0.82%
* **Performance Note:** The model achieves **99.32% - 100% DR** across standard Ethernet attacks (Replay, Frame Injection, MAC Flooding, PTP Injection). The overall metric is heavily impacted by a known blind spot on "CAN DoS Tunneled" attacks (0% DR) due to payload-only feature extraction.

### Fusion Model Performance (Test Set)
The late fusion head aggregates expert output for uncertain samples via a Gated MLP structure (1,459 parameters).
* **F1-Score:** 94.76%
* **Detection Rate (Recall):** 93.06%
* **Precision:** 96.53%
* **Expected Calibration Error (ECE):** 0.164

### Model Complexity Highlights
* **Total Edge Deployment Parameters:** 52,469
* **ONNX File Size:** ~212 KB Total Deployment Size
* **Escalation Ratio:** Only 0.26% of CAN samples and 0% of ETH samples trigger heavy path routing.

## 🚀 Getting Started

The repository is intentionally dependency-light at import time. Commands that require ML packages fail with actionable messages until optional dependencies are installed.

```powershell
python -m pip install -e .[ml]
dpcr-ids prepare-data --config configs/research_pipeline.yaml
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol can
dpcr-ids serve-runtime --config configs/runtime.yaml
```

## 🔌 Edge Validation

Fusion ONNX export, Raspberry Pi benchmarking, and Pi-side replay validation are supported through:

```powershell
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol fusion
dpcr-ids-benchmark-fusion --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx --output-json artifacts/dpcr_ids_research_v1/export/fusion_benchmark.json
dpcr-ids-replay-fusion --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx --dataset artifacts/dpcr_ids_research_v1/prepared/fusion/test.jsonl --output-json artifacts/dpcr_ids_research_v1/export/fusion_replay.json
```

Detailed Raspberry Pi setup and replay workflow:
- [Raspberry Pi Deployment Guide](docs/raspberry_pi_deployment.md)


Based on the `REPRODUCE.md` guide from the codebase, here are the exact commands required to reproduce the full model training pipeline. 

Ensure you have your virtual environment activated and the required ML dependencies installed (`pip install -e ".[ml]"`) before running these. All commands should be executed from the project root (`c:\ResearchAutoIDS`).

### 1. Train the Heavy "Teacher" Models
First, you train the large transformer models that will be used to distill knowledge into the edge-friendly models.
```powershell
python -m dpcr_ids train-teacher --config configs/research_pipeline.yaml --protocol can
python -m dpcr_ids train-teacher --config configs/research_pipeline.yaml --protocol ethernet
```

### 2. Train the Independent "Student" Models
Next, you train the lightweight models (TCN for CAN, CNN for Ethernet) directly on ground-truth labels.
```powershell
python -m dpcr_ids train-student --config configs/research_pipeline.yaml --protocol can
python -m dpcr_ids train-student --config configs/research_pipeline.yaml --protocol ethernet
```

### 3. Perform Knowledge Distillation
This step uses the Teacher models to guide and optimize the Student models for better accuracy while maintaining their small footprint.
```powershell
python -m dpcr_ids distill --config configs/research_pipeline.yaml --protocol can
python -m dpcr_ids distill --config configs/research_pipeline.yaml --protocol ethernet
```

### 4. Calibrate the Models (Temperature Scaling)
Calibration ensures the probability outputs (confidence scores) of the distilled models are reliable.
```powershell
python -m dpcr_ids calibrate --config configs/research_pipeline.yaml --protocol can
python -m dpcr_ids calibrate --config configs/research_pipeline.yaml --protocol ethernet
```

### 5. Train the Random Forest Fallback Classifiers
This trains a fallback mechanism for the specific samples where the student models report high uncertainty.
```powershell
python -m dpcr_ids train-fallback --config configs/research_pipeline.yaml --protocol can
python -m dpcr_ids train-fallback --config configs/research_pipeline.yaml --protocol ethernet
```

### 6. Train and Calibrate the Late Fusion Head
Finally, you train the Gated MLP fusion model that combines the representations of both the CAN and Ethernet experts. This step **must** be run after the individual CAN and Ethernet students are fully trained.
```powershell
python -m dpcr_ids train-student --config configs/research_pipeline.yaml --protocol fusion
python -m dpcr_ids calibrate --config configs/research_pipeline.yaml --protocol fusion
```

Once you run these commands sequentially, all resulting `.pt` (PyTorch checkpoints), calibration JSONs, and fallback `.pkl` models will be securely saved into your `artifacts/dpcr_ids_research_v1/` directory as specified in the configuration.