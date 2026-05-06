"""Export CAN and Ethernet student models to ONNX for OMNeT++ simulation.

This script exports dual-output models (logit + embedding) needed by the
OMNeT++ DPCR-IDS simulation. The standard ONNX export only exports the
forward() method (logit output). For the simulation, we need both the
logit AND the 128-dim embedding from forward_features().

Usage:
    python export_onnx_for_omnetpp.py [--config configs/research_pipeline.yaml]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dpcr_ids.config import load_config
from dpcr_ids.utils.deps import require_dependency
from dpcr_ids.utils.fs import ensure_dir


def export_dual_output_model(model, input_shape: tuple, output_path: Path, protocol: str):
    """Export a model with two outputs: logit and embedding."""
    torch = require_dependency("torch")
    require_dependency("onnx")

    import torch.nn as nn

    class DualOutputWrapper(nn.Module):
        """Wraps a student model to output both logit and embedding."""
        def __init__(self, base_model):
            super().__init__()
            self.base = base_model

        def forward(self, x):
            embedding = self.base.forward_features(x)  # [batch, 128]
            logit = self.base.classifier(embedding).squeeze(-1)  # [batch]
            return logit, embedding

    model.eval()
    wrapper = DualOutputWrapper(model)
    wrapper.eval()

    dummy_input = torch.randn(*input_shape)

    ensure_dir(output_path.parent)

    torch.onnx.export(
        wrapper,
        dummy_input,
        str(output_path),
        input_names=["input"],
        output_names=["logits", "embedding"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "logits": {0: "batch_size"},
            "embedding": {0: "batch_size"},
        },
        opset_version=13,
        dynamo=False,
    )

    # Verify
    import onnxruntime as ort
    session = ort.InferenceSession(str(output_path))
    import numpy as np
    test_input = np.random.randn(*input_shape).astype(np.float32)
    outputs = session.run(None, {"input": test_input})
    print(f"  [{protocol}] Verified ONNX export:")
    print(f"    logit shape:     {outputs[0].shape}")
    print(f"    embedding shape: {outputs[1].shape}")
    print(f"    output path:     {output_path}")

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/research_pipeline.yaml")
    parser.add_argument("--output-dir", default="dpcr-ids-sim/simulations/models")
    args = parser.parse_args()

    torch = require_dependency("torch")
    config = load_config(args.config)
    output_dir = Path(args.output_dir)

    from dpcr_ids.training.pipeline import _load_trained_model

    # --- Export CAN Student ---
    print("\n=== Exporting CAN Student to ONNX (dual-output) ===")
    can_model, _, _ = _load_trained_model(config, "can")
    can_model.eval()
    can_path = output_dir / "can_student.onnx"
    # CAN input: [batch=1, channels=16, sequence=100]
    export_dual_output_model(can_model, (1, 16, 100), can_path, "can")

    # --- Export Ethernet Student ---
    print("\n=== Exporting Ethernet Student to ONNX (dual-output) ===")
    eth_model, _, _ = _load_trained_model(config, "ethernet")
    eth_model.eval()
    eth_path = output_dir / "eth_student.onnx"
    # Ethernet input: [batch=1, channels=4, height=32, width=32]
    export_dual_output_model(eth_model, (1, 4, 32, 32), eth_path, "ethernet")

    # --- Copy/re-export Fusion Student ---
    print("\n=== Exporting Fusion Student to ONNX ===")
    fusion_model, _, _ = _load_trained_model(config, "fusion")
    fusion_model.eval()
    fusion_path = output_dir / "fusion_student.onnx"
    # Fusion: standard single-output export (no embedding needed)
    from dpcr_ids.export.onnx import export_model_to_onnx
    export_model_to_onnx(fusion_model, (1, 2, 129), fusion_path)
    print(f"  [fusion] Exported to: {fusion_path}")

    print(f"\n[OK] All models exported to: {output_dir}/")
    print("  Copy this directory to your OMNeT++ opp_env workspace.")


if __name__ == "__main__":
    main()
