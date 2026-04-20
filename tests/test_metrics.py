from __future__ import annotations

import unittest

from dpcr_ids.training.calibration import fit_temperature_from_logits
from dpcr_ids.training.metrics import binary_classification_report


class MetricsTests(unittest.TestCase):
    def test_binary_classification_report(self) -> None:
        report = binary_classification_report([0, 1, 1, 0], [0.1, 0.9, 0.6, 0.2])
        self.assertGreater(report["f1"], 0.7)
        self.assertEqual(report["fp"], 0)

    def test_temperature_scaling_returns_artifact(self) -> None:
        logits = [-1.2, 1.4, 0.3, -0.6, 2.0]
        labels = [0, 1, 1, 0, 1]
        scaler, artifact = fit_temperature_from_logits(logits, labels)
        self.assertGreater(scaler.temperature, 0.0)
        self.assertEqual(artifact.protocol, "unknown")
        self.assertGreaterEqual(artifact.ece_before, 0.0)
        self.assertGreaterEqual(artifact.ece_after, 0.0)


if __name__ == "__main__":
    unittest.main()
