from fastapi import APIRouter, HTTPException

from app.broker.paper_broker import PaperBroker
from app.risk.controller import RiskController
from app.risk.limit import RiskLimit
from app.trading.execution_engine import TradingExecutionEngine
from app.trading.order import Order

router = APIRouter(prefix="/trading", tags=["trading"])

broker = PaperBroker()
risk_controller = RiskController(RiskLimit(max_position=100, max_drawdown=0.2))
execution_engine = TradingExecutionEngine(broker, risk_controller)


@router.post("/orders")
async def submit_order(payload: dict):
    symbol = str(payload.get("symbol", "")).strip()
    side = str(payload.get("side", "")).upper()
    volume = int(payload.get("volume", 0))
    price = float(payload.get("price", 0) or 0)
    offset = str(payload.get("offset", "OPEN")).upper()
    if not symbol or side not in {"BUY", "SELL", "LONG", "SHORT"} or volume <= 0:
        raise HTTPException(status_code=400, detail="symbol, side and positive volume are required")
    order = Order(symbol=symbol, side=side, volume=volume, price=price, offset=offset)
    result = execution_engine.execute(order)
    return {
        "success": result.success,
        "message": result.message,
        "order": {
            "id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "volume": order.volume,
            "price": order.price,
            "offset": order.offset,
            "status": order.status,
            "reason": order.reason,
        },
    }


@router.get("/orders")
async def list_orders():
    return {"orders": broker.query_orders()}


@router.get("/positions")
async def list_positions():
    return {"positions": broker.query_position()}


@router.get("/risk")
async def risk_state():
    return {
        "max_position": risk_controller.limit.max_position,
        "max_drawdown": risk_controller.limit.max_drawdown,
        "positions": broker.query_position(),
    }
