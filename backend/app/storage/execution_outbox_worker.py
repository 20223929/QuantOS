from __future__ import annotations

import asyncio


class ExecutionOutboxWorker:
    """Async lifecycle worker that periodically drains the execution outbox."""

    def __init__(self, dispatcher, interval_seconds: float = 1.0, limit: int = 100):
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.dispatcher = dispatcher
        self.interval_seconds = interval_seconds
        self.limit = limit
        self._task: asyncio.Task | None = None
        self._running = False
        self.last_result: dict[str, int] | None = None
        self.last_error: str | None = None

    @property
    def running(self) -> bool:
        return self._running

    async def run_once(self) -> dict[str, int]:
        result = self.dispatcher.dispatch_once(limit=self.limit)
        self.last_result = result
        self.last_error = None
        return result

    async def _run(self) -> None:
        try:
            while self._running:
                try:
                    await self.run_once()
                except Exception as exc:
                    self.last_error = f"{type(exc).__name__}: {exc}"
                if self._running:
                    await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            raise
        finally:
            self._running = False

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="quantos-execution-outbox")

    async def stop(self) -> None:
        self._running = False
        task = self._task
        self._task = None
        if task is None:
            return
        if not task.done():
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
