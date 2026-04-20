from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dpcr_ids.runtime.aggregator import DecisionAggregator
from dpcr_ids.runtime.router import ConfidenceRouter
from dpcr_ids.runtime.service import RuntimeIDSService
from dpcr_ids.types import RuntimeAlert


class RouterRuntimeTests(unittest.TestCase):
    def test_router_semantics(self) -> None:
        router = ConfidenceRouter(tau_low=0.15, tau_high=0.85)
        self.assertEqual(router.route(0.9).decision, "ATTACK")
        self.assertEqual(router.route(0.1).decision, "NORMAL")
        self.assertEqual(router.route(0.5).path, "heavy")

    def test_expert_override_both_normal(self) -> None:
        """When both experts predict NORMAL (< tau_low), override fusion ATTACK."""
        router = ConfidenceRouter(tau_low=0.15, tau_high=0.85)
        # Fusion says ATTACK (calProb=0.99), but both experts say NORMAL
        result = router.route(
            p_attack_calibrated=0.99,
            p_attack_raw=0.99,
            expert_probs={"can": 0.01, "ethernet": 0.05},
        )
        self.assertEqual(result.decision, "NORMAL")
        self.assertEqual(result.path, "fast")

    def test_expert_override_one_expert_above_threshold(self) -> None:
        """When one expert is above τ_low, override does NOT activate."""
        router = ConfidenceRouter(tau_low=0.15, tau_high=0.85)
        # CAN expert predicts ATTACK (0.9), ETH is normal (0.05)
        result = router.route(
            p_attack_calibrated=0.99,
            p_attack_raw=0.99,
            expert_probs={"can": 0.9, "ethernet": 0.05},
        )
        self.assertEqual(result.decision, "ATTACK")
        self.assertEqual(result.path, "fast")

    def test_no_expert_probs_preserves_original_behavior(self) -> None:
        """Without expert_probs, behavior is identical to original router."""
        router = ConfidenceRouter(tau_low=0.15, tau_high=0.85)
        # No expert_probs → original logic: calProb=0.99 → ATTACK
        result = router.route(p_attack_calibrated=0.99)
        self.assertEqual(result.decision, "ATTACK")
        # Uncertain zone → heavy path
        result = router.route(p_attack_calibrated=0.5)
        self.assertIsNone(result.decision)
        self.assertEqual(result.path, "heavy")

    def test_aggregator_prefers_higher_risk(self) -> None:
        aggregator = DecisionAggregator(bucket_ms=250)
        alerts = [
            RuntimeAlert(1.0, "can", "NORMAL", "fast", 0.1, 0.1, 0.3, False, {}),
            RuntimeAlert(1.1, "ethernet", "ATTACK", "fast", 0.8, 0.8, 0.4, False, {}),
        ]
        merged = aggregator.merge_alerts(alerts)
        self.assertEqual(merged.protocol, "gateway")
        self.assertEqual(merged.decision, "ATTACK")

    def test_runtime_service_fail_open_and_logging(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "health.jsonl"
            service = RuntimeIDSService(
                routers={"can": ConfidenceRouter(0.15, 0.85)},
                aggregator=DecisionAggregator(bucket_ms=250),
                deadline_ms=0.0,
                fail_open=True,
                health_log_path=str(log_path),
            )
            alert = service.process_event(protocol="unknown", raw_probability=0.4, timestamp=1.0)
            self.assertEqual(alert.path, "fail_open")
            self.assertTrue(log_path.exists())

    def test_runtime_service_uses_fallback_probability(self) -> None:
        service = RuntimeIDSService(
            routers={"can": ConfidenceRouter(0.15, 0.85)},
            aggregator=DecisionAggregator(bucket_ms=250),
            fail_open=True,
        )
        alert = service.process_event(protocol="can", raw_probability=0.5, fallback_probability=0.8, timestamp=1.0)
        self.assertEqual(alert.decision, "ATTACK")
        self.assertEqual(alert.path, "heavy")


if __name__ == "__main__":
    unittest.main()
