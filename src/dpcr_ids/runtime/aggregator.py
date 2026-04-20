"""Gateway-level late fusion by fixed time bucket."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from dpcr_ids.types import RuntimeAlert

DECISION_PRIORITY = {"NORMAL": 0, "ATTACK": 1, "ESCALATE": 2}


class DecisionAggregator:
    def __init__(self, bucket_ms: int = 250) -> None:
        self.bucket_ms = bucket_ms
        self._buckets: dict[int, list[RuntimeAlert]] = defaultdict(list)

    def bucket_id(self, timestamp: float) -> int:
        return int((timestamp * 1000) // self.bucket_ms)

    def add(self, alert: RuntimeAlert) -> None:
        self._buckets[self.bucket_id(alert.timestamp)].append(alert)

    def merge_alerts(self, alerts: list[RuntimeAlert]) -> RuntimeAlert:
        selected = max(alerts, key=lambda alert: (DECISION_PRIORITY.get(alert.decision, -1), alert.p_attack_calibrated))
        merged_metadata = {
            "bucket_size": len(alerts),
            "protocols": sorted({alert.protocol for alert in alerts}),
            "sources": [alert.metadata for alert in alerts],
        }
        return replace(
            selected,
            protocol="gateway",
            metadata=merged_metadata,
            escalate_flag=selected.decision == "ESCALATE" or any(alert.escalate_flag for alert in alerts),
        )

    def flush(self, up_to_timestamp: float | None = None) -> list[RuntimeAlert]:
        if up_to_timestamp is None:
            bucket_ids = sorted(self._buckets.keys())
        else:
            limit = self.bucket_id(up_to_timestamp)
            bucket_ids = [bucket_id for bucket_id in sorted(self._buckets.keys()) if bucket_id <= limit]
        merged: list[RuntimeAlert] = []
        for bucket_id in bucket_ids:
            alerts = self._buckets.pop(bucket_id, [])
            if alerts:
                merged.append(self.merge_alerts(alerts))
        return merged
