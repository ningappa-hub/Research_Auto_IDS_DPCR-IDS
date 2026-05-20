$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
# NOTE: Do NOT set CUDA_VISIBLE_DEVICES=-1
# .venv Python has PyTorch 2.11.0+cu128 which fully supports RTX 5090 (CC 12.0)
# System python has old 2.13.0.dev+cu126 which does NOT — always use .venv\Scripts\python

$PYTHON = ".venv\Scripts\python"

# Verify GPU is visible before starting
Write-Host "=== GPU / Environment Check ===" -ForegroundColor Yellow
& $PYTHON -c "import torch; cc=torch.cuda.get_device_capability(0); print(f'GPU: {torch.cuda.get_device_name(0)}  CC:{cc[0]}.{cc[1]}  VRAM:{torch.cuda.get_device_properties(0).total_memory//1024**3}GB  PyTorch:{torch.__version__}')"
if ($LASTEXITCODE -ne 0) { throw "GPU check failed - ensure .venv is set up with PyTorch 2.11+cu128" }

function Step($label, $cmd) {
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "`n[$ts] === $label ===" -ForegroundColor Cyan
    $fullCmd = $cmd -replace "^python ", "$PYTHON "
    Invoke-Expression $fullCmd
    if ($LASTEXITCODE -ne 0) { throw "FAILED: $label (exit $LASTEXITCODE)" }
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $label DONE" -ForegroundColor Green
}

Write-Host "`n=== Full Pipeline Retrain (GPU-accelerated) ===" -ForegroundColor Yellow
Write-Host "CAN:      epochs=75, patience=12 (prevent undertraining)"
Write-Host "Ethernet: LR=5e-5, cosine LR, grad-clip=1.0, smoothing=0.05, dropout=0.2"
Write-Host "Boundary: split gap=2 windows (no window-overlap leakage)`n"

# ── CAN ──────────────────────────────────────────────────────────────────────
# Step "Prepare CAN data"     "python -m dpcr_ids prepare-data --config configs/research_pipeline.yaml --protocol can"
# Step "Distill CAN student"  "python -m dpcr_ids distill --config configs/research_pipeline.yaml --protocol can 2>&1 | Tee-Object artifacts/dpcr_ids_research_v1/logs/distill_can_v2.log"
# Step "Calibrate CAN"        "python -m dpcr_ids calibrate --config configs/research_pipeline.yaml --protocol can"
# Step "Evaluate CAN"         "python -m dpcr_ids evaluate --config configs/research_pipeline.yaml --protocol can"

# ── Ethernet ──────────────────────────────────────────────────────────────────
# Step "Prepare Ethernet data"   "python -m dpcr_ids prepare-data --config configs/research_pipeline.yaml --protocol ethernet"
# Step "Train Ethernet teacher"  "python -m dpcr_ids train-teacher --config configs/research_pipeline.yaml --protocol ethernet 2>&1 | Tee-Object artifacts/dpcr_ids_research_v1/logs/train_ethernet_teacher_v2.log"
Step "Distill Ethernet student" "python -m dpcr_ids distill --config configs/research_pipeline.yaml --protocol ethernet 2>&1 | Tee-Object artifacts/dpcr_ids_research_v1/logs/distill_ethernet_v2.log"
Step "Calibrate Ethernet"      "python -m dpcr_ids calibrate --config configs/research_pipeline.yaml --protocol ethernet"
Step "Train Ethernet fallback" "python -m dpcr_ids train-fallback --config configs/research_pipeline.yaml --protocol ethernet"
Step "Evaluate Ethernet"       "python -m dpcr_ids evaluate --config configs/research_pipeline.yaml --protocol ethernet"

# ── Fusion ───────────────────────────────────────────────────────────────────
Step "Train Fusion model"  "python -m dpcr_ids train-student --config configs/research_pipeline.yaml --protocol fusion 2>&1 | Tee-Object artifacts/dpcr_ids_research_v1/logs/train_fusion_v2.log"
Step "Calibrate Fusion"    "python -m dpcr_ids calibrate --config configs/research_pipeline.yaml --protocol fusion"
Step "Evaluate Fusion"     "python -m dpcr_ids evaluate --config configs/research_pipeline.yaml --protocol fusion"

Write-Host "`n=== All done! Results in artifacts/dpcr_ids_research_v1/evaluations/ ===" -ForegroundColor Green
