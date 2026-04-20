"""Export helpers."""

from __future__ import annotations

from dpcr_ids.export.onnx import export_model_to_onnx

__all__ = ["benchmark_fusion_onnx", "export_model_to_onnx", "replay_fusion_onnx"]


def __getattr__(name: str):
    if name == "benchmark_fusion_onnx":
        from dpcr_ids.export.benchmark import benchmark_fusion_onnx

        return benchmark_fusion_onnx
    if name == "replay_fusion_onnx":
        from dpcr_ids.export.replay import replay_fusion_onnx

        return replay_fusion_onnx
    raise AttributeError(name)
