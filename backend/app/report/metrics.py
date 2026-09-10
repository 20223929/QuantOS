from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    win_rate: float = 0.0


def calculate_metrics(equity_curve):
    if not equity_curve:
        return PerformanceMetrics()

    start = equity_curve[0]
    end = equity_curve[-1]
    total_return = (end - start) / start if start else 0

    peak = start
    max_drawdown = 0
    for value in equity_curve:
        peak = max(peak, value)
        if peak:
            max_drawdown = max(max_drawdown, (peak - value) / peak)

    return PerformanceMetrics(
        total_return=total_return,
        max_drawdown=max_drawdown,
    )
