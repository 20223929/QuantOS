from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select

import app.api.v1.trading as trading_api
from app.risk.controller import RiskController
from app.risk.limit import RiskLimit
from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.execution_outbox_dispatcher import ExecutionOutboxDispatcher
from app.storage.models.outbox import ExecutionOutboxModel
from app.storage.models.trading import OrderModel, PositionModel, TradeModel
from app.storage.orm import ORMManager
from app.trading.execution_engine import TradingExecutionEngine
from app.trading.execution_event_sink import ExecutionEventSink
from app.trading.order import Order
from app.trading.position import Position


class _ExecutionEngine:
    def __init__(self, status: str = "FILLED"):
        self.status = status
        self.positions: dict[str, Position] = {}

    def execute(self, order):
        order.status = self.status
        if self.status == "FILLED":
            position = self.positions.setdefault(order.symbol, Position(symbol=order.symbol))
            if order.side.upper() in {"BUY", "LONG"}:
                position.volume += order.volume
            else:
                position.volume -= order.volume
        elif self.status == "REJECTED":
            order.reason = "risk check rejected order"
        return type("Result", (), {"success": self.status != "REJECTED", "message": order.reason or self.status.lower()})()


class _CancellableBroker:
    def __init__(self, status: str = "SUBMITTED"):
        self.orders = {
            "pending-1": {
                "id": "pending-1",
                "symbol": "SHFE.rb",
                "side": "BUY",
                "volume": 2,
                "price": 3500.0,
                "offset": "OPEN",
                "status": status,
            }
        }

    def query_orders(self):
        return dict(self.orders)

    def cancel_order(self, order_id):
        stored = self.orders.get(order_id)
        if stored is None:
            return {"id": order_id, "status": "NOT_FOUND"}
        if stored["status"] == "FILLED":
            return {"id": order_id, "status": "NOT_CANCELLABLE"}
        stored["status"] = "CANCELLED"
        return dict(stored)


class _FailIfSubmittedBroker:
    def submit_order(self, order):
        raise AssertionError("broker must not be called after risk rejection")


@pytest.fixture
def isolated_trading(monkeypatch, tmp_path):
    orm = ORMManager(f"sqlite:///{Path(tmp_path) / 'trading-api.db'}")
    orm.create_tables()
    engine = _ExecutionEngine()
    monkeypatch.setattr(trading_api, "_orm", orm)
    monkeypatch.setattr(trading_api, "execution_engine", engine)
    monkeypatch.setattr(trading_api, "execution_event_sink", ExecutionEventSink())
    dispatcher = ExecutionOutboxDispatcher(orm.session, trading_api.execution_event_sink.handle)
    monkeypatch.setattr(trading_api, "execution_outbox_dispatcher", dispatcher)
    return orm, engine


def test_submit_order_persists_full_execution_chain_and_dispatches(isolated_trading):
    orm, _ = isolated_trading

    response = asyncio.run(
        trading_api.submit_order(
            {"symbol": "SHFE.rb", "side": "BUY", "volume": 5, "price": 3500, "offset": "OPEN"}
        )
    )
    assert response["success"] is True
    assert response["order"]["status"] == "FILLED"
    assert response["order"]["id"]

    with orm.session() as session:
        assert session.scalar(select(func.count(OrderModel.id))) == 1
        assert session.scalar(select(func.count(TradeModel.id))) == 1
        assert session.scalar(select(func.count(PositionModel.id))) == 1
        assert session.scalar(select(func.count(ExecutionOutboxModel.id))) == 1

        order = session.scalar(select(OrderModel))
        position = session.scalar(select(PositionModel))
        event = session.scalar(select(ExecutionOutboxModel))
        assert order.status == "FILLED"
        assert order.reason == ""
        assert position.volume == 5
        assert event.status == "PENDING"


def test_partial_fill_then_fill_persists_incremental_trades_and_outbox(isolated_trading):
    orm, engine = isolated_trading
    order = Order(symbol="SHFE.rb", side="BUY", volume=5, price=3500, order_id="partial-1")

    order.status = "PARTIALLY_FILLED"
    order.filled_volume = 2
    engine.positions[order.symbol] = Position(symbol=order.symbol, volume=2)
    trading_api.persist_execution(order)

    order.status = "FILLED"
    order.filled_volume = 5
    engine.positions[order.symbol].volume = 5
    trading_api.persist_execution(order)
    trading_api.persist_execution(order)

    with orm.session() as session:
        record = session.scalar(select(OrderModel).where(OrderModel.order_id == "partial-1"))
        trades = list(session.scalars(select(TradeModel).order_by(TradeModel.id)))
        position = session.scalar(select(PositionModel).where(PositionModel.symbol == "SHFE.rb"))
        events = list(session.scalars(select(ExecutionOutboxModel).order_by(ExecutionOutboxModel.id)))
        assert record.status == "FILLED"
        assert len(trades) == 2
        assert [trade.volume for trade in trades] == [2, 3]
        assert sum(trade.volume for trade in trades) == 5
        assert position.volume == 5
        assert len(events) == 2
        assert [event.event_id for event in events] == [
            "order-executed:partial-1:2",
            "order-executed:partial-1:5",
        ]

    first_dispatch = asyncio.run(trading_api.dispatch_execution_outbox())
    second_dispatch = asyncio.run(trading_api.dispatch_execution_outbox())
    assert first_dispatch == {"delivered": 2, "retried": 0, "selected": 2}
    assert second_dispatch == {"delivered": 0, "retried": 0, "selected": 0}
    assert len(trading_api.execution_event_sink.snapshot()) == 2


def test_rejected_order_persists_and_returns_reason(isolated_trading):
    orm, _ = isolated_trading
    trading_api.execution_engine.status = "REJECTED"

    response = asyncio.run(
        trading_api.submit_order(
            {"symbol": "SHFE.rb", "side": "BUY", "volume": 5, "price": 3500}
        )
    )
    order_id = response["order"]["id"]
    assert order_id
    assert response["success"] is False
    assert response["order"]["status"] == "REJECTED"
    assert response["order"]["reason"] == "risk check rejected order"

    fetched = asyncio.run(trading_api.get_order(order_id))
    assert fetched["order"]["status"] == "REJECTED"
    assert fetched["order"]["reason"] == "risk check rejected order"
    assert fetched["order"]["filled_volume"] == 0

    with orm.session() as session:
        assert session.scalar(select(func.count(OrderModel.id))) == 1
        assert session.scalar(select(func.count(TradeModel.id))) == 0
        assert session.scalar(select(func.count(PositionModel.id))) == 0
        assert session.scalar(select(func.count(ExecutionOutboxModel.id))) == 0
        record = session.scalar(select(OrderModel))
        assert record.order_id == order_id
        assert record.reason == "risk check rejected order"


def test_invalid_order_request_is_rejected_before_execution(isolated_trading):
    orm, engine = isolated_trading

    async def scenario():
        with pytest.raises(trading_api.HTTPException) as exc_info:
            await trading_api.submit_order({"symbol": "", "side": "BUY", "volume": 1})
        return exc_info.value

    exc = asyncio.run(scenario())
    assert exc.status_code == 400
    assert engine.positions == {}
    with orm.session() as session:
        assert session.scalar(select(func.count(OrderModel.id))) == 0


def test_outbox_status_reflects_pending_then_processed(isolated_trading):
    orm, _ = isolated_trading
    response = asyncio.run(
        trading_api.submit_order(
            {"symbol": "SHFE.rb", "side": "BUY", "volume": 2, "price": 3500}
        )
    )
    assert response["success"] is True

    async def status_and_dispatch():
        pending = await trading_api.execution_outbox_status()
        dispatched = await trading_api.dispatch_execution_outbox()
        final = await trading_api.execution_outbox_status()
        return pending, dispatched, final

    pending, dispatched, final = asyncio.run(status_and_dispatch())
    assert pending["pending"] == 1
    assert pending["processed"] == 0
    assert dispatched == {"delivered": 1, "retried": 0, "selected": 1}
    assert final["pending"] == 0
    assert final["processed"] == 1
    assert final["sink_events"] == 1

    with orm.session() as session:
        repository = ExecutionOutboxRepository(session)
        event = session.scalar(select(ExecutionOutboxModel))
        assert event.status == "PROCESSED"
        assert repository.pending() == []


def test_get_order_and_list_positions_match_persisted_state(isolated_trading):
    response = asyncio.run(
        trading_api.submit_order(
            {"symbol": "SHFE.rb", "side": "BUY", "volume": 3, "price": 3500}
        )
    )
    order_id = response["order"]["id"]
    assert order_id
    listed = asyncio.run(trading_api.list_orders())
    fetched = asyncio.run(trading_api.get_order(order_id))
    positions = asyncio.run(trading_api.list_positions())

    assert listed["orders"][0]["id"] == order_id
    assert listed["orders"][0]["filled_volume"] == 3
    assert fetched["order"]["id"] == order_id
    assert fetched["order"]["status"] == "FILLED"
    assert fetched["order"]["reason"] == ""
    assert fetched["order"]["filled_volume"] == 3
    assert positions["positions"]["SHFE.rb"] == 3


def test_cancel_submitted_order_updates_persisted_lifecycle(isolated_trading, monkeypatch):
    orm, _ = isolated_trading
    broker = _CancellableBroker()
    monkeypatch.setattr(trading_api, "broker", broker)

    with orm.session() as session:
        repository = trading_api.TradingRepository(session)
        repository.save_order(
            type(
                "Order",
                (),
                {
                    "order_id": "pending-1",
                    "symbol": "SHFE.rb",
                    "side": "BUY",
                    "volume": 2,
                    "price": 3500.0,
                    "status": "SUBMITTED",
                    "reason": "",
                    "offset": "OPEN",
                },
            )()
        )
        session.commit()

    response = asyncio.run(trading_api.cancel_order("pending-1"))
    assert response["success"] is True
    assert response["order"]["status"] == "CANCELLED"

    fetched = asyncio.run(trading_api.get_order("pending-1"))
    assert fetched["order"]["status"] == "CANCELLED"

    with orm.session() as session:
        assert session.scalar(select(func.count(TradeModel.id))) == 0
        assert session.scalar(select(func.count(PositionModel.id))) == 0
        record = session.scalar(select(OrderModel))
        assert record.status == "CANCELLED"


def test_cancel_filled_order_returns_conflict_and_keeps_filled_state(isolated_trading, monkeypatch):
    orm, _ = isolated_trading
    broker = _CancellableBroker(status="FILLED")
    monkeypatch.setattr(trading_api, "broker", broker)

    with orm.session() as session:
        repository = trading_api.TradingRepository(session)
        repository.save_order(
            type(
                "Order",
                (),
                {
                    "order_id": "pending-1",
                    "symbol": "SHFE.rb",
                    "side": "BUY",
                    "volume": 2,
                    "price": 3500.0,
                    "status": "FILLED",
                    "reason": "",
                    "offset": "OPEN",
                },
            )()
        )
        session.commit()

    async def scenario():
        with pytest.raises(trading_api.HTTPException) as exc_info:
            await trading_api.cancel_order("pending-1")
        return exc_info.value

    exc = asyncio.run(scenario())
    assert exc.status_code == 409
    fetched = asyncio.run(trading_api.get_order("pending-1"))
    assert fetched["order"]["status"] == "FILLED"


def test_risk_position_boundary_rejects_without_broker_execution(isolated_trading, monkeypatch):
    orm, _ = isolated_trading
    risk_controller = RiskController(RiskLimit(max_position=100, max_drawdown=0.2))
    engine = TradingExecutionEngine(_FailIfSubmittedBroker(), risk_controller)
    engine.positions["SHFE.rb"] = Position(symbol="SHFE.rb", volume=100)
    monkeypatch.setattr(trading_api, "risk_controller", risk_controller)
    monkeypatch.setattr(trading_api, "execution_engine", engine)

    response = asyncio.run(
        trading_api.submit_order(
            {"symbol": "SHFE.rb", "side": "BUY", "volume": 1, "price": 3500}
        )
    )
    order_id = response["order"]["id"]
    assert order_id
    assert response["success"] is False
    assert response["order"]["status"] == "REJECTED"
    assert response["order"]["reason"] == "position limit exceeded"
    assert engine.positions["SHFE.rb"].volume == 100

    rejected = asyncio.run(trading_api.get_order(order_id))
    assert rejected["order"]["id"] == order_id
    assert rejected["order"]["status"] == "REJECTED"
    assert rejected["order"]["reason"] == "position limit exceeded"

    with orm.session() as session:
        record = session.scalar(select(OrderModel))
        assert record.order_id == order_id
        assert record.status == "REJECTED"
        assert record.reason == "position limit exceeded"
        assert session.scalar(select(func.count(TradeModel.id))) == 0
        assert session.scalar(select(func.count(ExecutionOutboxModel.id))) == 0
