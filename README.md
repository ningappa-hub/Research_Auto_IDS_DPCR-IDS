# DPCR-IDS

Research-first implementation scaffold for a calibrated late-fusion dual-protocol IDS covering CAN and automotive Ethernet.

The repository is intentionally dependency-light at import time. Commands that require ML packages fail with actionable messages until optional dependencies are installed.

```powershell
python -m pip install -e .[ml]
dpcr-ids prepare-data --config configs/research_pipeline.yaml
dpcr-ids train-student --config configs/research_pipeline.yaml --protocol can
dpcr-ids serve-runtime --config configs/runtime.yaml
```

## Edge Validation

Fusion ONNX export, Raspberry Pi benchmarking, and Pi-side replay validation are supported through:

```powershell
dpcr-ids export-onnx --config configs/research_pipeline.yaml --protocol fusion
dpcr-ids-benchmark-fusion --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx --output-json artifacts/dpcr_ids_research_v1/export/fusion_benchmark.json
dpcr-ids-replay-fusion --model artifacts/dpcr_ids_research_v1/export/fusion_student.onnx --dataset artifacts/dpcr_ids_research_v1/prepared/fusion/test.jsonl --output-json artifacts/dpcr_ids_research_v1/export/fusion_replay.json
```

Detailed Raspberry Pi setup and replay workflow:
- [Raspberry Pi Deployment Guide](C:/ResearchAutoIDS/docs/raspberry_pi_deployment.md)
