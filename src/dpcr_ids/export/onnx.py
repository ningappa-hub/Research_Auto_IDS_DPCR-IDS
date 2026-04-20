"""ONNX export helpers."""

from __future__ import annotations

from pathlib import Path

from dpcr_ids.utils.deps import require_dependency
from dpcr_ids.utils.fs import ensure_dir


def export_model_to_onnx(model, input_shape: tuple[int, ...], output_path: str | Path) -> str:
    torch = require_dependency("torch")
    require_dependency("onnx")
    model.eval()
    target = Path(output_path)
    ensure_dir(target.parent)
    dummy_input = torch.randn(*input_shape)
    torch.onnx.export(
        model,
        dummy_input,
        str(target),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch_size"}, "logits": {0: "batch_size"}},
        opset_version=13,
        dynamo=False,
    )
    return str(target)
