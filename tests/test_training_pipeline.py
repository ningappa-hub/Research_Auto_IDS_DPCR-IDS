from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import torch
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    torch = None

from dpcr_ids.training import pipeline
from dpcr_ids.training.fallback import ProtocolFallbackModel


@unittest.skipIf(torch is None, "torch is required for training pipeline tests")
class TrainingPipelineTests(unittest.TestCase):
    def _feature_tensor(self, base: float) -> list[list[float]]:
        return [[base + (channel * 0.01) for _ in range(100)] for channel in range(16)]

    def _write_split(self, path: Path, count: int) -> None:
        rows = []
        for index in range(count):
            label = index % 2
            rows.append({"features": self._feature_tensor(float(label) + (index * 0.001)), "label": label})
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    def _write_config(self, root: Path) -> tuple[Path, dict]:
        artifacts_dir = root / "artifacts"
        prepared_dir = artifacts_dir / "prepared" / "can"
        prepared_dir.mkdir(parents=True, exist_ok=True)
        self._write_split(prepared_dir / "train.jsonl", 8)
        self._write_split(prepared_dir / "val.jsonl", 4)
        self._write_split(prepared_dir / "test.jsonl", 4)

        config = {
            "artifacts_dir": str(artifacts_dir),
            "seed": 42,
            "training": {
                "batch_size": 2,
                "epochs": 6,
                "learning_rate": 0.0005,
                "weight_decay": 0.0,
                "early_stopping_patience": 2,
                "distillation": {"alpha": 0.5, "temperature": 4.0},
            },
            "routing": {
                "tau_low": 0.15,
                "tau_high": 0.85,
                "fallback_uncertainty_low": 0.3,
                "fallback_uncertainty_high": 0.7,
                "bucket_ms": 250,
            },
        }
        config_path = root / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return config_path, config

    def test_streaming_dataset_predicts_without_row_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path, config = self._write_config(Path(tmpdir))
            del config_path
            dataset = pipeline._prepared_dataset(config, "can", "val")
            try:
                self.assertEqual(len(dataset), 4)
                model = pipeline._build_model("can")
                labels, logits, probabilities, embeddings = pipeline._predict_dataset(
                    model,
                    dataset,
                    "can",
                    batch_size=2,
                    device=torch.device("cpu"),
                )
            finally:
                pipeline._close_dataset(dataset)

            self.assertEqual(len(labels), 4)
            self.assertEqual(len(logits), 4)
            self.assertEqual(len(probabilities), 4)
            self.assertEqual(len(embeddings), 4)
            self.assertEqual(len(embeddings[0]), 128)

    def test_training_honors_early_stopping_patience(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path, config = self._write_config(Path(tmpdir))
            del config
            with patch("dpcr_ids.training.pipeline._resolve_device", return_value=torch.device("cpu")):
                with patch(
                    "dpcr_ids.training.pipeline.evaluate_predictions",
                    side_effect=lambda *args, **kwargs: {"f1": 0.5},
                ):
                    summary = pipeline.train_student_from_path(str(config_path), "can")

            self.assertTrue(summary["early_stopped"])
            self.assertEqual(summary["best_epoch"], 1)
            self.assertEqual(summary["epochs_ran"], 3)
            self.assertEqual(summary["validation"]["f1"], 0.5)
            checkpoint_path = Path(summary["checkpoint"])
            self.assertTrue(checkpoint_path.exists())
            self.assertTrue(checkpoint_path.with_suffix(".json").exists())

    def test_evaluate_ignores_stale_calibration_and_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path, config = self._write_config(root)
            calibration_dir = root / "artifacts" / "calibration"
            fallback_dir = root / "artifacts" / "fallback"
            calibration_dir.mkdir(parents=True, exist_ok=True)
            fallback_dir.mkdir(parents=True, exist_ok=True)
            calibration_path = calibration_dir / "can.json"
            fallback_path = fallback_dir / "can_rf.pkl"
            calibration_path.write_text(json.dumps({"temperature": 9.0}), encoding="utf-8")
            stale_fallback = ProtocolFallbackModel()
            stale_fallback.fit([[0.0] * 128], [0])
            stale_fallback.save(fallback_path)

            with patch("dpcr_ids.training.pipeline._resolve_device", return_value=torch.device("cpu")):
                summary = pipeline.train_student_from_path(str(config_path), "can")
                model_path = Path(summary["checkpoint"])
                stale_time = model_path.stat().st_mtime - 60.0
                os.utime(calibration_path, (stale_time, stale_time))
                os.utime(fallback_path, (stale_time, stale_time))
                result = pipeline.evaluate_from_path(str(config_path), "can")

            self.assertFalse(result["calibration_used"])
            self.assertFalse(result["fallback_used"])
            self.assertIn("report", result)

    def test_one_class_fallback_returns_boundary_probability(self) -> None:
        fallback = ProtocolFallbackModel()
        fallback.fit([[0.0] * 4, [1.0] * 4], [0, 0])
        self.assertEqual(fallback.predict_probability([0.2] * 4), 0.0)

    def test_load_trained_model_prefers_newest_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path, config = self._write_config(root)
            del config_path
            models_dir = root / "artifacts" / "models"
            models_dir.mkdir(parents=True, exist_ok=True)

            student_model = pipeline._build_model("can")
            distilled_model = pipeline._build_model("can")
            student_path = models_dir / "can_student.pt"
            distilled_path = models_dir / "can_student_distilled.pt"
            torch.save({"state_dict": student_model.state_dict()}, student_path)
            torch.save({"state_dict": distilled_model.state_dict()}, distilled_path)

            old_time = student_path.stat().st_mtime - 60.0
            os.utime(distilled_path, (old_time, old_time))
            model, kind, selected_path = pipeline._load_trained_model(config, "can")

            self.assertEqual(kind, "student")
            self.assertEqual(selected_path, student_path)
            self.assertIsNotNone(model)


if __name__ == "__main__":
    unittest.main()
