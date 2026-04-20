"""Passive runtime service with fail-open behavior."""

from __future__ import annotations

import time
from typing import Any
from typing import Callable

from dpcr_ids.runtime.aggregator import DecisionAggregator
from dpcr_ids.runtime.router import ConfidenceRouter
from dpcr_ids.types import RuntimeAlert
from dpcr_ids.utils.fs import append_jsonl

FallbackHandler = Callable[[Any], tuple[str, float, bool]]


class RuntimeIDSService:
    def __init__(
        self,
        routers: dict[str, ConfidenceRouter],
        aggregator: DecisionAggregator,
        fallback_handlers: dict[str, FallbackHandler] | None = None,
        deadline_ms: float = 20.0,
        fail_open: bool = True,
        health_log_path: str | None = None,
    ) -> None:
        self.routers = routers
        self.aggregator = aggregator
        self.fallback_handlers = fallback_handlers or {}
        self.deadline_ms = deadline_ms
        self.fail_open = fail_open
        self.health_log_path = health_log_path

    def _log_health(self, payload: dict[str, Any]) -> None:
        if self.health_log_path:
            append_jsonl(self.health_log_path, payload)

    def process_event(
        self,
        protocol: str,
        raw_probability: float,
        calibrated_probability: float | None = None,
        timestamp: float | None = None,
        metadata: dict[str, Any] | None = None,
        fallback_input: Any = None,
        fallback_probability: float | None = None,
    ) -> RuntimeAlert:
        event_ts = time.time() if timestamp is None else timestamp
        event_meta = dict(metadata or {})
        start = time.perf_counter()
        try:
            router = self.routers[protocol]
            p_cal = raw_probability if calibrated_probability is None else calibrated_probability
            route = router.route(p_cal, p_attack_raw=raw_probability)
            decision = route.decision
            path = route.path
            escalate = False

            if decision is None:
                if fallback_probability is not None:
                    if 0.3 < fallback_probability < 0.7:
                        decision = "ESCALATE"
                        escalate = True
                    else:
                        decision = "ATTACK" if fallback_probability >= 0.7 else "NORMAL"
                elif protocol in self.fallback_handlers:
                    decision, fallback_probability, escalate = self.fallback_handlers[protocol](fallback_input)
                else:
                    decision = "ESCALATE"
                    fallback_probability = raw_probability
                    escalate = True

            latency_ms = (time.perf_counter() - start) * 1000.0
            if latency_ms > self.deadline_ms:
                self._log_health({"timestamp": event_ts, "protocol": protocol, "status": "deadline_exceeded", "latency_ms": latency_ms})

            alert = RuntimeAlert(
                timestamp=event_ts,
                protocol=protocol,
                decision=decision,
                path=path,
                p_attack_raw=raw_probability,
                p_attack_calibrated=p_cal,
                latency_ms=latency_ms,
                escalate_flag=escalate,
                metadata=event_meta,
            )
            self.aggregator.add(alert)
            return alert
        except Exception as exc:
            self._log_health({"timestamp": event_ts, "protocol": protocol, "status": "error", "error": str(exc)})
            if not self.fail_open:
                raise
            alert = RuntimeAlert(
                timestamp=event_ts,
                protocol=protocol,
                decision="NORMAL",
                path="fail_open",
                p_attack_raw=raw_probability,
                p_attack_calibrated=calibrated_probability if calibrated_probability is not None else raw_probability,
                latency_ms=(time.perf_counter() - start) * 1000.0,
                escalate_flag=False,
                metadata={**event_meta, "error": str(exc), "fail_open": True},
            )
            self.aggregator.add(alert)
            return alert
