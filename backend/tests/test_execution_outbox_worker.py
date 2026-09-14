import asyncio

from app.storage.execution_outbox_worker import ExecutionOutboxWorker


class Dispatcher:
    def __init__(self, failures=0):
        self.calls = []
        self.failures = failures

    def dispatch_once(self, limit=100):
        self.calls.append(limit)
        if self.failures:
            self.failures -= 1
            raise RuntimeError("temporary database failure")
        return {"delivered": 1, "retried": 0, "selected": 1}


def test_worker_run_once_records_dispatch_result():
    async def scenario():
        dispatcher = Dispatcher()
        worker = ExecutionOutboxWorker(dispatcher, interval_seconds=60, limit=7)

        result = await worker.run_once()

        assert result == {"delivered": 1, "retried": 0, "selected": 1}
        assert dispatcher.calls == [7]
        assert worker.last_result == result
        assert worker.last_error is None

    asyncio.run(scenario())


def test_worker_start_is_idempotent_and_stop_cancels_task():
    async def scenario():
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

    asyncio.run(scenario())


def test_worker_survives_transient_dispatch_failure_and_recovers():
    async def scenario():
        dispatcher = Dispatcher(failures=1)
        worker = ExecutionOutboxWorker(dispatcher, interval_seconds=0.01, limit=5)

        worker.start()
        await asyncio.sleep(0.04)
        await worker.stop()

        assert len(dispatcher.calls) >= 2
        assert worker.last_result == {"delivered": 1, "retried": 0, "selected": 1}
        assert worker.last_error is None

    asyncio.run(scenario())


def test_worker_stop_without_start_is_safe():
    async def scenario():
        worker = ExecutionOutboxWorker(Dispatcher())
        await worker.stop()
        assert worker.running is False

    asyncio.run(scenario())
