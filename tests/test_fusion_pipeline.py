from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import torch
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    torch = None

from dpcr_ids.models import CanStudentTCN
from dpcr_ids.models import EthStudentCNN
from dpcr_ids.training import pipeline


@unittest.skipIf(torch is None, "torch is required for fusion pipeline tests")
class FusionPipelineTests(unittest.TestCase):
    def _can_features(self, base: float) -> list[list[float]]:
        return [[base + (channel * 0.01) for _ in range(100)] for channel in range(16)]

    def _eth_features(self, base: float) -> list[list[list[float]]]:
        return [[[base + (channel * 0.01) for _ in range(32)] for _ in range(32)] for channel in range(3)]

    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    def _write_protocol_split(self, protocol_dir: Path, split: str, feature_factory, labels: list[int]) -> None:
        rows = [
            {"features": feature_factory(float(label) + (index * 0.001)), "label": label}
            for index, label in enumerate(labels)
        ]
        self._write_jsonl(protocol_dir / f"{split}.jsonl", rows)

    def _write_student_checkpoint(self, path: Path, model) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state_dict": model.state_dict()}, path)

    def _build_config(self, root: Path) -> Path:
        artifacts_dir = root / "artifacts"
        can_dir = artifacts_dir / "prepared" / "can"
        eth_dir = artifacts_dir / "prepared" / "ethernet"
        self._write_protocol_split(can_dir, "train", self._can_features, [0, 0, 1, 0, 0, 1])
        self._write_protocol_split(can_dir, "val", self._can_features, [0, 1, 0, 1])
        self._write_protocol_split(can_dir, "test", self._can_features, [0, 1, 1, 0])
        self._write_protocol_split(eth_dir, "train", self._eth_features, [0, 1, 0, 1, 0, 1])
        self._write_protocol_split(eth_dir, "val", self._eth_features, [0, 0, 1, 1])
        self._write_protocol_split(eth_dir, "test", self._eth_features, [1, 0, 1, 0])

        models_dir = artifacts_dir / "models"
        self._write_student_checkpoint(models_dir / "can_student.pt", CanStudentTCN())
        self._write_student_checkpoint(models_dir / "ethernet_student.pt", EthStudentCNN())

        config = {
            "artifacts_dir": str(artifacts_dir),
            "seed": 42,
            "fusion": {
                "enabled": True,
                "expert_order": ["can", "ethernet"],
                "expert_dim": 129,
                "hidden_dim": 8,
                "fusion_dim": 16,
                "bucket_ms": 20,
                "use_raw_logits": True,
                "pseudo_time_step": 0.01,
            },
            "training": {
                "batch_size": 2,
                "epochs": 4,
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
        return config_path

    def test_prepare_fusion_dataset_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._build_config(Path(tmpdir))
            config = json.loads(config_path.read_text(encoding="utf-8"))
            with patch("dpcr_ids.training.pipeline._resolve_device", return_value=torch.device("cpu")):
                pipeline._prepare_fusion_if_needed(config, ("train", "val", "test"))
                first = (Path(config["artifacts_dir"]) / "prepared" / "fusion" / "train.jsonl").read_text(encoding="utf-8")
                pipeline._prepare_fusion_if_needed(config, ("train", "val", "test"))
                second = (Path(config["artifacts_dir"]) / "prepared" / "fusion" / "train.jsonl").read_text(encoding="utf-8")
            self.assertEqual(first, second)
            rows = [json.loads(line) for line in first.splitlines() if line.strip()]
            self.assertEqual(len(rows), 3)
            self.assertEqual(len(rows[0]["features"]), 2)
            self.assertEqual(len(rows[0]["features"][0]), 129)
            self.assertIn(rows[0]["pair_type"], {"AA", "AN", "NA", "NN"})

    def test_prepare_fusion_dataset_preserves_ethernet_attack_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._build_config(Path(tmpdir))
            config = json.loads(config_path.read_text(encoding="utf-8"))
            artifacts_dir = Path(config["artifacts_dir"])
            can_dir = artifacts_dir / "prepared" / "can"
            eth_dir = artifacts_dir / "prepared" / "ethernet"
            self._write_protocol_split(can_dir, "test", self._can_features, [0, 0, 1, 1])
            self._write_protocol_split(eth_dir, "test", self._eth_features, [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1])
            with patch("dpcr_ids.training.pipeline._resolve_device", return_value=torch.device("cpu")):
                pipeline._prepare_fusion_if_needed(config, ("test",))
            manifest = json.loads((artifacts_dir / "prepared" / "fusion" / "test.manifest.json").read_text(encoding="utf-8"))
            summary = manifest["metadata"]["summary"]
            self.assertEqual(summary["ethernet_attack_bucket_count"], 2)
            self.assertGreater(summary["paired_ethernet_attack_bucket_count"], 0)
            self.assertGreater(summary["pair_type_counts"]["NA"] + summary["pair_type_counts"]["AA"], 0)
            self.assertEqual(summary["pairing_method"], "coverage_aware_pseudo_time")

    def test_fusion_training_evaluation_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._build_config(Path(tmpdir))
            with patch("dpcr_ids.training.pipeline._resolve_device", return_value=torch.device("cpu")):
                summary = pipeline.train_student_from_path(str(config_path), "fusion")
                calibration = pipeline.calibrate_from_path(str(config_path), "fusion")
                evaluation = pipeline.evaluate_from_path(str(config_path), "fusion")
                export = pipeline.export_onnx_from_path(str(config_path), "fusion")
            self.assertTrue(Path(summary["checkpoint"]).exists())
            self.assertIn("validation", summary)
            self.assertIn("temperature", calibration)
            self.assertIn("paired_bucket_count", evaluation["report"])
            self.assertIn("pair_type_counts", evaluation["report"])
            self.assertEqual(evaluation["report"]["expert_order"], ["can", "ethernet"])
            self.assertEqual(evaluation["report"]["pairing_method"], "coverage_aware_pseudo_time")
            self.assertTrue(Path(export["onnx_path"]).exists())
            self.assertEqual(export["input_shape"], [1, 2, 129])


if __name__ == "__main__":
    unittest.main()
