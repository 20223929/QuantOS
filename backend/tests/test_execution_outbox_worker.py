import asyncio

import pytest

from app.storage.execution_outbox_worker import ExecutionOutboxWorker


class Dispatcher:
    def __init__(self):
        self.calls = []

    def dispatch_once(self, limit=100):
        self.calls.append(limit)
        return {"delivered": 1, "retried": 0, "selected": 1}


@pytest.mark.asyncio
async def test_worker_run_once_records_dispatch_result():
    dispatcher = Dispatcher()
    worker = ExecutionOutboxWorker(dispatcher, interval_seconds=60, limit=7)

    result = await worker.run_once()

    assert result == {"delivered": 1, "retried": 0, "selected": 1}
    assert dispatcher.calls == [7]
    assert worker.last_result == result


@pytest.mark.asyncio
async def test_worker_start_is_idempotent_and_stop_cancels_task():
    dispatcher = Dispatcher()
    worker = ExecutionOutboxWorker(dispatcher, interval_seconds=0.01, limit=3)

    worker.start()
    first_task = worker._task
    worker.start()

    assert worker.running is True
    assert worker._task is first_task

    await asyncio.sleep(0.03)
    await worker.stop()

    assert worker.running is False
    assert worker._task is None
    assert len(dispatcher.calls) >= 1


@pytest.mark.asyncio
async def test_worker_stop_without_start_is_safe():
    worker = ExecutionOutboxWorker(Dispatcher())
    await worker.stop()
    assert worker.running is False
