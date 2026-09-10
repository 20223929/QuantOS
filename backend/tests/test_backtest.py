from app.backtest.performance import PerformanceMetrics


def test_metrics():
    result = PerformanceMetrics()
    assert result is not None
