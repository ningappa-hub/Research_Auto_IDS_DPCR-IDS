$ErrorActionPreference = "Stop"
.venv\Scripts\activate
Write-Host "Preparing Ethernet data..."
python -m dpcr_ids.cli prepare-data --config configs/research_pipeline.yaml --protocol ethernet

Write-Host "Training Ethernet teacher..."
python -m dpcr_ids.cli train-teacher --config configs/research_pipeline.yaml --protocol ethernet

Write-Host "Training Ethernet student..."
python -m dpcr_ids.cli train-student --config configs/research_pipeline.yaml --protocol ethernet

Write-Host "Distilling Ethernet student..."
python -m dpcr_ids.cli distill --config configs/research_pipeline.yaml --protocol ethernet

Write-Host "Calibrating Ethernet..."
python -m dpcr_ids.cli calibrate --config configs/research_pipeline.yaml --protocol ethernet

Write-Host "Training Ethernet fallback..."
python -m dpcr_ids.cli train-fallback --config configs/research_pipeline.yaml --protocol ethernet

Write-Host "Training Fusion model..."
python -m dpcr_ids.cli train-student --config configs/research_pipeline.yaml --protocol fusion

Write-Host "Calibrating Fusion model..."
python -m dpcr_ids.cli calibrate --config configs/research_pipeline.yaml --protocol fusion

Write-Host "Evaluating Ethernet..."
python -m dpcr_ids.cli evaluate --config configs/research_pipeline.yaml --protocol ethernet

Write-Host "Evaluating Fusion..."
python -m dpcr_ids.cli evaluate --config configs/research_pipeline.yaml --protocol fusion

Write-Host "Done."
