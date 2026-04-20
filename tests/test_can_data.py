from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dpcr_ids.data.can import build_can_windows
from dpcr_ids.data.can import extract_can_frame_features
from dpcr_ids.data.can import prepare_can_dataset
from dpcr_ids.data.can import read_car_hacking_csv
from dpcr_ids.data.can import split_can_windows_attack_horizon

FIXTURE = Path("tests/fixtures/car_hacking/sample.csv")


class CanDataTests(unittest.TestCase):
    def test_read_and_extract_features(self) -> None:
        records = read_car_hacking_csv(FIXTURE)
        self.assertEqual(len(records), 6)
        self.assertEqual(records[0].can_id, int("0316", 16))

        feature_rows = extract_can_frame_features(records)
        self.assertEqual(len(feature_rows), 6)
        self.assertEqual(len(feature_rows[0].features), 16)
        self.assertEqual(feature_rows[2].label, 1)

    def test_windowing_uses_conservative_labels(self) -> None:
        feature_rows = extract_can_frame_features(read_car_hacking_csv(FIXTURE))
        windows = build_can_windows(feature_rows, window_size=4, stride=2)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0].label, 1)
        self.assertEqual(len(windows[0].features), 16)
        self.assertEqual(len(windows[0].features[0]), 4)

    def test_attack_horizon_split_preserves_attack_windows_in_eval(self) -> None:
        feature_rows = extract_can_frame_features(read_car_hacking_csv(FIXTURE))
        windows = build_can_windows(feature_rows, window_size=4, stride=1)
        split_samples, tail_holdout, metadata = split_can_windows_attack_horizon(
            windows,
            split_cfg={"train": 0.5, "val": 0.25, "test": 0.25},
        )
        self.assertTrue(any(sample.label for sample in split_samples["val"]))
        self.assertTrue(any(sample.label for sample in split_samples["test"]))
        self.assertGreaterEqual(metadata["last_attack_window"], metadata["first_attack_window"])
        self.assertGreaterEqual(len(tail_holdout), 0)

    def test_prepare_dataset_writes_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_root = str(FIXTURE.parent)
            report = prepare_can_dataset(
                dataset_root=dataset_root,
                files=[FIXTURE.name],
                output_dir=tmpdir,
                split_cfg={"train": 0.5, "val": 0.25, "test": 0.25},
                window_size=4,
                stride=1,
            )
            self.assertEqual(report["protocol"], "can")
            self.assertIn("train", report["manifests"])
            self.assertTrue(Path(tmpdir, "can", "train.manifest.json").exists())
            self.assertIn("tail_holdout", report["qa"])


if __name__ == "__main__":
    unittest.main()
