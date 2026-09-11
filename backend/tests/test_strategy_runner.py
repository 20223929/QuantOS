from app.strategy.runner import StrategyRunner


class DummyStrategy:
    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_strategy_runner_lifecycle():
    runner = StrategyRunner(DummyStrategy())
    runner.start()
    assert runner.state.running is True
    runner.stop()
    assert runner.state.running is False
