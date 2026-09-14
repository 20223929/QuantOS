from fastapi import APIRouter, HTTPException

from app.backtest.engine import BacktestEngine
from app.strategies.ma_cross import MACrossStrategy

router = APIRouter(prefix="/backtest", tags=["backtest"])


def _bar_close(bar):
    return float(bar.get("close", 0)) if isinstance(bar, dict) else float(getattr(bar, "close", bar))


@router.post("/run")
async def run_backtest(payload: dict):
    bars = payload.get("bars", [])
    if not bars:
        raise HTTPException(status_code=400, detail="bars must not be empty")
    short_window = int(payload.get("short_window", 5))
    long_window = int(payload.get("long_window", 20))
    initial_capital = float(payload.get("initial_capital", 100_000))
    multiplier = float(payload.get("contract_multiplier", 1))
    strategy = MACrossStrategy(short_window=short_window, long_window=long_window)
    result = BacktestEngine(strategy, initial_capital, multiplier).run(bars)
    return {"status": "completed", **result.summary(), "trade_log": result.trades}


@router.post("/validate")
async def validate_bars(payload: dict):
    bars = payload.get("bars", [])
    closes = [_bar_close(bar) for bar in bars]
    if not closes:
        raise HTTPException(status_code=400, detail="bars must not be empty")
    if any(price <= 0 for price in closes):
        raise HTTPException(status_code=400, detail="bar close prices must be positive")
    return {"valid": True, "bars": len(closes), "first_close": closes[0], "last_close": closes[-1]}
