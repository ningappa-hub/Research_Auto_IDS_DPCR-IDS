from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dpcr_ids.export.benchmark import benchmark_fusion_onnx
from dpcr_ids.export.onnx import export_model_to_onnx
from dpcr_ids.models.late_fusion import TinyLateFusionMetaModel


def _has_ml_stack() -> bool:
    try:
        import numpy  # noqa: F401
        import onnxruntime  # noqa: F401
        import torch  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


@unittest.skipUnless(_has_ml_stack(), "ML dependencies are required for ONNX benchmark tests")
class BenchmarkTests(unittest.TestCase):
    def test_benchmark_fusion_onnx_writes_expected_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            model_path = root / "fusion.onnx"
            json_path = root / "benchmark.json"
            csv_path = root / "benchmark.csv"

            model = TinyLateFusionMetaModel()
            export_model_to_onnx(model, input_shape=(1, 2, 129), output_path=model_path)
            result = benchmark_fusion_onnx(
                model_path=model_path,
                output_json=json_path,
                output_csv=csv_path,
                runs=1,
                warmup_runs=1,
                timed_runs=3,
                seed=7,
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())
            self.assertEqual(result["input_shape"], [1, 2, 129])
            self.assertEqual(result["runs"], 1)
            self.assertEqual(result["warmup_runs"], 1)
            self.assertEqual(result["timed_runs"], 3)
            self.assertIn("latency_ms_p50", result)
            self.assertIn("rss_mb_peak", result)
            self.assertIn("cpu_percent_mean", result)


if __name__ == "__main__":
    unittest.main()
