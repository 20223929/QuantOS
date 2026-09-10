from fastapi import APIRouter

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run")
async def run_backtest():
    return {
        "status": "completed",
        "trades": 0,
        "total_return": 0
    }


@router.get("/result")
async def result():
    return {
        "trades": 0,
        "total_return": 0,
        "max_drawdown": 0
    }
