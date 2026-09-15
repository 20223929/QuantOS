"""Trading state snapshot API."""

from fastapi import APIRouter

from app.trading.state_projector import TradingStateProjector

router = APIRouter(prefix="/trading", tags=["trading-state"])

# Temporary process-level projection instance.
# Repository-backed persistence will replace this in the database integration stage.
_projector = TradingStateProjector()


@router.get("/state")
async def get_trading_state() -> dict:
    """Return current trading state snapshot for dashboard recovery."""
    return _projector.snapshot()


__all__ = ["router"]
