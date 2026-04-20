from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dpcr_ids.export.onnx import export_model_to_onnx
from dpcr_ids.export.replay import replay_fusion_onnx
from dpcr_ids.models.late_fusion import TinyLateFusionMetaModel


def _has_ml_stack() -> bool:
    try:
        import numpy  # noqa: F401
        import onnxruntime  # noqa: F401
        import torch  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


@unittest.skipUnless(_has_ml_stack(), "ML dependencies are required for ONNX replay tests")
class ReplayTests(unittest.TestCase):
    def _write_dataset(self, path: Path) -> None:
        rows = []
        for index in range(4):
            features = []
            for expert in range(2):
                channel = [float(index + expert)] + [float(index + expert + 0.01 * offset) for offset in range(128)]
                features.append(channel)
            rows.append(
                {
                    "features": features,
                    "label": 1 if index % 2 else 0,
                    "pair_type": "NA" if index % 2 else "NN",
                }
            )
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    def test_replay_fusion_onnx_writes_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            model_path = root / "fusion.onnx"
            dataset_path = root / "dataset.jsonl"
            output_json = root / "replay.json"
            output_csv = root / "replay.csv"
            predictions_path = root / "predictions.jsonl"
            baseline_path = root / "baseline.json"
            calibration_path = root / "calibration.json"

            model = TinyLateFusionMetaModel()
            export_model_to_onnx(model, input_shape=(1, 2, 129), output_path=model_path)
            self._write_dataset(dataset_path)
            baseline_path.write_text(json.dumps({"f1": 0.5, "recall": 0.5, "precision": 0.5, "fpr": 0.5, "ece": 0.5}), encoding="utf-8")
            calibration_path.write_text(json.dumps({"temperature": 1.1}), encoding="utf-8")

            result = replay_fusion_onnx(
                model_path=model_path,
                dataset_jsonl=dataset_path,
                output_json=output_json,
                output_csv=output_csv,
                predictions_jsonl=predictions_path,
                calibration_json=str(calibration_path),
                baseline_report_json=str(baseline_path),
                batch_size=1,
            )

            self.assertTrue(output_json.exists())
            self.assertTrue(output_csv.exists())
            self.assertTrue(predictions_path.exists())
            self.assertEqual(result["sample_count"], 4)
            self.assertEqual(result["batch_size"], 1)
            self.assertTrue(result["calibration_used"])
            self.assertIn("latency_ms_p50", result)
            self.assertIn("report", result)
            self.assertIn("baseline_comparison", result)
            self.assertIn("predicted_attack_count", result["report"])


if __name__ == "__main__":
    unittest.main()
