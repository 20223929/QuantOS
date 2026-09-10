from fastapi import APIRouter

from backend.app.api.v1 import backtest, market, strategy

api_router = APIRouter()

api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
