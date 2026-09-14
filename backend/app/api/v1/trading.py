from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.broker.paper_broker import PaperBroker
from app.risk.controller import RiskController
from app.risk.limit import RiskLimit
from app.storage.orm import ORMManager
from app.storage.trading_repository import TradingRepository
from app.trading.execution_engine import TradingExecutionEngine
from app.trading.order import Order
from app.trading.position import Position

router = APIRouter(prefix="/trading", tags=["trading"])

broker = PaperBroker()
risk_controller = RiskController(RiskLimit(max_position=100, max_drawdown=0.2))
execution_engine = TradingExecutionEngine(broker, risk_controller)

_DB_PATH = Path("data/quantos.db")
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_orm = ORMManager(f"sqlite:///{_DB_PATH}")
_orm.create_tables()


def _load_persisted_positions() -> None:
    with _orm.session() as session:
        repository = TradingRepository(session)
        recovered = repository.recover_positions_from_trades()
        if recovered:
            session.commit()
        for record in repository.list_positions():
            execution_engine.positions[record.symbol] = Position(
                symbol=record.symbol,
                volume=int(record.volume),
            )


_load_persisted_positions()


def serialize_order(order: dict | Order) -> dict:
    if isinstance(order, dict):
        return {
            "id": order.get("id"),
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "volume": order.get("volume"),
            "price": order.get("price"),
            "offset": order.get("offset", "OPEN"),
            "status": order.get("status"),
            "reason": order.get("reason", ""),
        }
    return {
        "id": order.order_id,
        "symbol": order.symbol,
        "side": order.side,
        "volume": order.volume,
        "price": order.price,
        "offset": order.offset,
        "status": order.status,
        "reason": order.reason,
    }


def serialize_order_record(record) -> dict:
    return {
        "id": record.order_id,
        "symbol": record.symbol,
        "side": record.side,
        "volume": record.volume,
        "price": record.price,
        "offset": record.offset,
        "status": record.status,
        "reason": "",
    }


def persist_execution(order: Order) -> None:
    with _orm.session() as session:
        repository = TradingRepository(session)
        try:
            record = repository.save_order(order)
            if order.status == "FILLED":
                repository.apply_trade(
                    {
                        "trade_id": f"trade-{order.order_id}",
                        "order_id": record.id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "price": order.price,
                        "volume": order.volume,
                    }
                )
                position = execution_engine.positions[order.symbol]
                repository.upsert_position(order.symbol, position.volume)
            session.commit()
        except Exception:
            session.rollback()
            raise


@router.post("/orders")
async def submit_order(payload: dict):
    symbol = str(payload.get("symbol", "")).strip()
    side = str(payload.get("side", "")).upper()
    volume = int(payload.get("volume", 0))
    price = float(payload.get("price", 0) or 0)
    offset = str(payload.get("offset", "OPEN")).upper()
    if not symbol or side not in {"BUY", "SELL", "LONG", "SHORT"} or volume <= 0:
        raise HTTPException(status_code=400, detail="symbol, side and positive volume are required")
    if offset not in {"OPEN", "CLOSE", "CLOSETODAY", "CLOSEYESTERDAY"}:
        raise HTTPException(status_code=400, detail="unsupported offset")

    order = Order(symbol=symbol, side=side, volume=volume, price=price, offset=offset)
    result = execution_engine.execute(order)
    try:
        persist_execution(order)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to persist execution: {exc}") from exc
    return {
        "success": result.success,
        "message": result.message,
        "order": serialize_order(order),
    }


@router.get("/orders")
async def list_orders():
    with _orm.session() as session:
        repository = TradingRepository(session)
        records = repository.list_orders()
        return {"orders": [serialize_order_record(record) for record in records]}


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    with _orm.session() as session:
        repository = TradingRepository(session)
        for record in repository.list_orders():
            if record.order_id == order_id:
                return {"order": serialize_order_record(record)}
    raise HTTPException(status_code=404, detail=f"order not found: {order_id}")


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    order = broker.query_orders().get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"order not found: {order_id}")

    result = broker.cancel_order(order_id)
    status = str(result.get("status", "")).upper()
    if status == "NOT_CANCELLABLE":
        raise HTTPException(status_code=409, detail=f"order cannot be cancelled: {order_id}")
    if status == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=f"order not found: {order_id}")

    with _orm.session() as session:
        repository = TradingRepository(session)
        repository.update_order_status(order_id, status)
        session.commit()
    return {"success": True, "order": serialize_order(result)}


@router.get("/positions")
async def list_positions():
    with _orm.session() as session:
        repository = TradingRepository(session)
        records = repository.list_positions()
        return {"positions": {record.symbol: record.volume for record in records}}


@router.get("/risk")
async def risk_state():
    with _orm.session() as session:
        repository = TradingRepository(session)
        positions = {record.symbol: record.volume for record in repository.list_positions()}
    return {
        "max_position": risk_controller.limit.max_position,
        "max_drawdown": risk_controller.limit.max_drawdown,
        "positions": positions,
    }
