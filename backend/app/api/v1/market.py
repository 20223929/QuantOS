from fastapi import APIRouter, HTTPException

from app.adapters.tqsdk_adapter import TqSdkAdapter

router = APIRouter(prefix="/market", tags=["market"])
market_adapter = TqSdkAdapter()


@router.post("/connect")
async def connect_market():
    await market_adapter.connect()
    return {"status": "connected"}


@router.get("/tick")
async def tick(symbol: str = "SHFE.rb"):
    try:
        data = await market_adapter.get_tick(symbol)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    data.pop("quote", None)
    return data


@router.post("/subscribe")
async def subscribe(symbol: str = "SHFE.rb"):
    try:
        data = await market_adapter.subscribe(symbol)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    data.pop("quote", None)
    return data


@router.get("/bars")
async def bars(symbol: str = "SHFE.rb", duration_seconds: int = 60, data_length: int = 200):
    if duration_seconds <= 0 or data_length <= 0 or data_length > 5000:
        raise HTTPException(status_code=400, detail="invalid bar parameters")
    try:
        frame = await market_adapter.get_bars(symbol, duration_seconds, data_length)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"symbol": symbol, "duration_seconds": duration_seconds, "bars": frame.tail(data_length).to_dict(orient="records")}
