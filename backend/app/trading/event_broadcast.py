from __future__ import annotations

import asyncio
from typing import Any


class TradingEventBroadcaster:
    """In-process broadcaster shared by API and websocket consumers."""

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._queues.discard(queue)

    def publish(self, event: dict[str, Any]) -> int:
        delivered = 0
        for queue in list(self._queues):
            try:
                queue.put_nowait(event)
                delivered += 1
            except Exception:
                self._queues.discard(queue)
        return delivered


trading_event_broadcaster = TradingEventBroadcaster()
