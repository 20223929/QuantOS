from fastapi import APIRouter, HTTPException

from app.engine.strategy_engine import StrategyEngine
from app.strategies.ma_cross import MACrossStrategy

router = APIRouter(prefix="/strategy", tags=["strategy"])
strategy_engine = StrategyEngine()
strategy_engine.register(MACrossStrategy())


@router.get("/list")
async def list_strategy():
    return {"strategies": strategy_engine.list()}


@router.post("/start/{name}")
async def start_strategy(name: str):
    if name not in strategy_engine.strategies:
        raise HTTPException(status_code=404, detail=f"strategy not found: {name}")
    return await strategy_engine.start(name)


@router.post("/stop/{name}")
async def stop_strategy(name: str):
    if name not in strategy_engine.strategies:
        raise HTTPException(status_code=404, detail=f"strategy not found: {name}")
    return await strategy_engine.stop(name)
