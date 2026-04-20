from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import torch
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    torch = None

try:
    import onnxruntime as ort
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    ort = None

from dpcr_ids.export.onnx import export_model_to_onnx
from dpcr_ids.models import TinyLateFusionMetaModel
from dpcr_ids.models import stack_expert_outputs


@unittest.skipIf(torch is None, "torch is required for late fusion model tests")
class LateFusionModelTests(unittest.TestCase):
    def test_stack_expert_outputs_fixed_cross_protocol_shape(self) -> None:
        logits = [
            torch.tensor([0.1, -0.2], dtype=torch.float32),
            torch.tensor([0.3, 0.4], dtype=torch.float32),
        ]
        embeddings = [
            torch.full((2, 128), 1.0),
            torch.full((2, 128), 2.0),
        ]
        packed = stack_expert_outputs(logits, embeddings)
        self.assertEqual(tuple(packed.shape), (2, 2, 129))
        self.assertAlmostEqual(float(packed[0, 0, 0]), 0.1, places=6)
        self.assertAlmostEqual(float(packed[0, 1, 1]), 2.0, places=6)

    def test_stack_expert_outputs_rejects_wrong_contract(self) -> None:
        with self.assertRaises(ValueError):
            stack_expert_outputs([torch.tensor([0.1])], [torch.ones(1, 128)])
        with self.assertRaises(ValueError):
            stack_expert_outputs(
                [torch.tensor([0.1]), torch.tensor([0.2])],
                [torch.ones(1, 64), torch.ones(1, 64)],
            )
        with self.assertRaises(ValueError):
            TinyLateFusionMetaModel(num_experts=3, expert_dim=129)

    def test_meta_model_forward_shape(self) -> None:
        model = TinyLateFusionMetaModel()
        x = torch.randn(4, 2, 129)
        logits = model(x)
        features = model.forward_features(x)
        self.assertEqual(tuple(logits.shape), (4,))
        self.assertEqual(tuple(features.shape), (4, 16))

    @unittest.skipIf(ort is None, "onnxruntime is required for ONNX parity test")
    def test_onnx_export_matches_pytorch(self) -> None:
        model = TinyLateFusionMetaModel()
        model.eval()
        x = torch.randn(3, 2, 129)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "fusion.onnx"
            export_model_to_onnx(model, input_shape=(1, 2, 129), output_path=output_path)
            session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
            onnx_logits = session.run(None, {session.get_inputs()[0].name: x.numpy()})[0]
            torch_logits = model(x).detach().numpy()
        self.assertEqual(tuple(onnx_logits.shape), (3,))
        self.assertLess(float(abs(onnx_logits - torch_logits).max()), 1e-4)


if __name__ == "__main__":
    unittest.main()
