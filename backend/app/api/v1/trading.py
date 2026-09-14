from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.broker.paper_broker import PaperBroker
from app.risk.controller import RiskController
from app.risk.limit import RiskLimit
from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.execution_outbox_dispatcher import ExecutionOutboxDispatcher
from app.storage.execution_projection import ExecutionEventProjectionRepository
from app.storage.orm import ORMManager
from app.storage.trading_repository import TradingRepository
from app.trading.durable_execution_event_sink import DurableExecutionEventSink
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
execution_event_sink = DurableExecutionEventSink(_orm.session)
execution_outbox_dispatcher = ExecutionOutboxDispatcher(_orm.session, execution_event_sink.handle)


def _load_persisted_trading_state() -> None:
    with _orm.session() as session:
        repository = TradingRepository(session)
        recovered = repository.recover_positions_from_trades()
        reconciled_orders = repository.reconcile_order_states_from_trades()
        if recovered or reconciled_orders:
            session.commit()
        fill_cache: dict[str, float] = {}
        for record in repository.list_orders():
            filled = repository.order_filled_volume(record.id)
            if filled > 0 and record.order_id:
                fill_cache[str(record.order_id)] = filled
        execution_engine.restore_filled_volumes(fill_cache)
        for record in repository.list_positions():
            execution_engine.positions[record.symbol] = Position(symbol=record.symbol, volume=record.volume)


_load_persisted_trading_state()


def serialize_order(order: dict | Order) -> dict:
    if isinstance(order, dict):
        return {"id": order.get("id"), "symbol": order.get("symbol"), "side": order.get("side"), "volume": order.get("volume"), "price": order.get("price"), "offset": order.get("offset", "OPEN"), "status": order.get("status"), "reason": order.get("reason", ""), "filled_volume": order.get("filled_volume", 0)}
    return {"id": order.order_id, "symbol": order.symbol, "side": order.side, "volume": order.volume, "price": order.price, "offset": order.offset, "status": order.status, "reason": order.reason, "filled_volume": order.filled_volume}


def serialize_order_record(record, filled_volume: float | None = None) -> dict:
    return {"id": record.order_id, "symbol": record.symbol, "side": record.side, "volume": record.volume, "price": record.price, "offset": record.offset, "status": record.status, "reason": record.reason, "filled_volume": float(filled_volume or 0.0)}


def serialize_projection(row) -> dict:
    return execution_event_sink._serialize_event(
        row.event_id,
        row.event_type,
        row.aggregate_id,
        __import__("json").loads(row.payload),
    )


def persist_execution(order: Order) -> None:
    with _orm.session() as session:
        repository = TradingRepository(session)
        outbox = ExecutionOutboxRepository(session)
        try:
            record = repository.save_order(order)
            status = str(order.status).upper()
            cumulative = float(getattr(order, "filled_volume", 0) or 0)
            if status == "FILLED" and cumulative <= 0:
                cumulative = float(order.volume)
                order.filled_volume = cumulative

            if status in {"PARTIALLY_FILLED", "FILLED"} and cumulative > 0:
                persisted = repository.order_filled_volume(record.id)
                delta = cumulative - persisted
                if delta > 0:
                    trade = {
                        "trade_id": f"trade-{order.order_id}-{cumulative:g}",
                        "order_id": record.id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "price": order.price,
                        "volume": delta,
                    }
                    repository.apply_trade(trade)
                    position = execution_engine.positions.get(order.symbol, Position(symbol=order.symbol))
                    repository.upsert_position(order.symbol, position.volume)
                    outbox.enqueue(
                        event_type="ORDER_EXECUTED",
                        aggregate_id=order.order_id,
                        event_id=f"order-executed:{order.order_id}:{cumulative:g}",
                        payload={
                            "order": serialize_order(order),
                            "trade": trade,
                            "position": {"symbol": order.symbol, "volume": position.volume},
                        },
                    )
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
    order = Order(
        symbol=symbol,
        side=side,
        volume=volume,
        price=price,
        offset=offset,
        order_id=f"order-{uuid4().hex}",
    )
    runtime_snapshot = execution_engine.snapshot_runtime_state()
    result = execution_engine.execute(order)
    try:
        persist_execution(order)
    except Exception as exc:
        execution_engine.restore_runtime_state(runtime_snapshot)
        raise HTTPException(status_code=500, detail=f"failed to persist execution: {exc}") from exc
    return {"success": result.success, "message": result.message, "order": serialize_order(order)}


@router.post("/outbox/dispatch")
async def dispatch_execution_outbox():
    return execution_outbox_dispatcher.dispatch_once()


@router.get("/outbox/status")
async def execution_outbox_status():
    with _orm.session() as session:
        repository = ExecutionOutboxRepository(session)
        counts = repository.status_counts()
    return {**counts, "metrics": execution_outbox_dispatcher.snapshot(), "sink_events": len(execution_event_sink.snapshot())}


@router.get("/events")
async def list_execution_events(
    event_type: str | None = None,
    aggregate_id: str | None = None,
    event_id: str | None = None,
    limit: int = 100,
):
    if limit <= 0 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    with _orm.session() as session:
        repository = ExecutionEventProjectionRepository(session)
        rows = repository.list_events(
            event_type=event_type,
            aggregate_id=aggregate_id,
            event_id=event_id,
            limit=limit,
        )
        return {"events": [serialize_projection(row) for row in rows]}


@router.get("/orders")
async def list_orders():
    with _orm.session() as session:
        repository = TradingRepository(session)
        records = repository.list_orders()
        return {"orders": [serialize_order_record(record, repository.order_filled_volume(record.id)) for record in records]}


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    with _orm.session() as session:
        repository = TradingRepository(session)
        record = repository.get_order(order_id)
        if record is not None:
            return {"order": serialize_order_record(record, repository.order_filled_volume(record.id))}
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
        updated = repository.update_order_status(order_id, status)
        if updated is None:
            session.rollback()
            raise HTTPException(status_code=404, detail=f"order not found: {order_id}")
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
    return {"max_position": risk_controller.limit.max_position, "max_drawdown": risk_controller.limit.max_drawdown, "positions": positions}
