def build_equity_curve(trades, initial_capital=100000):
    equity = [initial_capital]
    current = initial_capital

    for trade in trades:
        current += trade.get("pnl", 0)
        equity.append(current)

    return equity
