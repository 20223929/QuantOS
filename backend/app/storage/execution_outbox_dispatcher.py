from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from app.storage.execution_outbox import ExecutionOutboxRepository


@dataclass
class ExecutionOutboxMetrics:
    delivered: int = 0
    retried: int = 0
    selected: int = 0
    claim_renewed: int = 0
    claim_lost: int = 0


class ExecutionOutboxDispatcher:
    """Deliver durable execution events with per-event retry isolation."""

    def __init__(
        self,
        session_factory,
        handler: Callable[[str, str, dict], None],
        claim_seconds: int = 30,
        heartbeat_seconds: float | None = None,
    ):
        if claim_seconds <= 0:
            raise ValueError("claim_seconds must be positive")
        if heartbeat_seconds is not None and heartbeat_seconds <= 0:
            raise ValueError("heartbeat_seconds must be positive")
        self.session_factory = session_factory
        self.handler = handler
        self.claim_seconds = claim_seconds
        self.heartbeat_seconds = heartbeat_seconds or max(0.5, claim_seconds / 3)
        if self.heartbeat_seconds >= claim_seconds:
            raise ValueError("heartbeat_seconds must be less than claim_seconds")
        self.owner = f"dispatcher-{uuid4()}"
        self.metrics = ExecutionOutboxMetrics()

    def _start_heartbeat(self, event_id: str, stop_event: threading.Event) -> threading.Thread:
        def renew_loop() -> None:
            while not stop_event.wait(self.heartbeat_seconds):
                try:
                    with self.session_factory() as session:
                        repository = ExecutionOutboxRepository(session)
                        renewed = repository.renew_claim(
                            event_id,
                            owner=self.owner,
                            claim_seconds=self.claim_seconds,
                        )
                        session.commit()
                    if renewed is not None:
                        self.metrics.claim_renewed += 1
                    else:
                        self.metrics.claim_lost += 1
                        return
                except Exception:
                    self.metrics.claim_lost += 1
                    return

        thread = threading.Thread(
            target=renew_loop,
            name=f"quantos-outbox-heartbeat-{event_id}",
            daemon=True,
        )
        thread.start()
        return thread

    def _finalize(self, event_id: str, *, retry: bool) -> bool:
        try:
            with self.session_factory() as session:
                repository = ExecutionOutboxRepository(session)
                result = (
                    repository.mark_retry(event_id, owner=self.owner)
                    if retry
                    else repository.mark_processed(event_id, owner=self.owner)
                )
                if result is None:
                    return False
                session.commit()
                return True
        except Exception:
            return False

    def dispatch_once(self, limit: int = 100) -> dict[str, int]:
        if limit <= 0:
            return {"delivered": 0, "retried": 0, "selected": 0}

        with self.session_factory() as session:
            repository = ExecutionOutboxRepository(session)
            events = repository.claim_pending(
                limit=limit,
                owner=self.owner,
                claim_seconds=self.claim_seconds,
            )
            session.commit()

        delivered = 0
        retried = 0
        claim_lost = 0

        for event in events:
            stop_event = threading.Event()
            heartbeat = self._start_heartbeat(event.event_id, stop_event)
            try:
                self.handler(event.event_type, event.aggregate_id, json.loads(event.payload))
            except Exception:
                retry_marked = self._finalize(event.event_id, retry=True)
                if retry_marked:
                    retried += 1
                else:
                    claim_lost += 1
            else:
                processed = self._finalize(event.event_id, retry=False)
                if processed:
                    delivered += 1
                else:
                    claim_lost += 1
            finally:
                stop_event.set()
                heartbeat.join(timeout=min(self.heartbeat_seconds, 1.0))

        self.metrics.delivered += delivered
        self.metrics.retried += retried
        self.metrics.selected += len(events)
        self.metrics.claim_lost += claim_lost
        return {"delivered": delivered, "retried": retried, "selected": len(events)}

    def snapshot(self) -> dict[str, int]:
        return {
            "delivered": self.metrics.delivered,
            "retried": self.metrics.retried,
            "selected": self.metrics.selected,
            "claim_renewed": self.metrics.claim_renewed,
            "claim_lost": self.metrics.claim_lost,
        }
