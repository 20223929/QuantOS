from fastapi import APIRouter

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/tick")
async def tick(symbol: str = "SHFE.rb"):
    return {
        "symbol": symbol,
        "price": 0,
        "source": "tqsdk"
    }


@router.post("/subscribe")
async def subscribe(symbol: str = "SHFE.rb"):
    return {
        "symbol": symbol,
        "status": "subscribed"
    }
