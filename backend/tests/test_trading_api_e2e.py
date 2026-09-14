from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select

import app.api.v1.trading as trading_api
from app.storage.models.outbox import ExecutionOutboxModel
from app.storage.models.trading import OrderModel, PositionModel, TradeModel
from app.storage.orm import ORMManager
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
        return type("Result", (), {"success": self.status != "REJECTED", "message": self.status.lower()})()


@pytest.fixture
def isolated_trading(monkeypatch, tmp_path):
    orm = ORMManager(f"sqlite:///{Path(tmp_path) / 'trading-api.db'}")
    orm.create_tables()
    engine = _ExecutionEngine()
    monkeypatch.setattr(trading_api, "_orm", orm)
    monkeypatch.setattr(trading_api, "execution_engine", engine)
    return orm, engine


def test_submit_order_persists_full_execution_chain_and_dispatches(isolated_trading):
    orm, _ = isolated_trading

    async def scenario():
        return await trading_api.submit_order(
            {"symbol": "SHFE.rb", "side": "BUY", "volume": 5, "price": 3500, "offset": "OPEN"}
        )

    response = asyncio.run(scenario())
    assert response["success"] is True
    assert response["order"]["status"] == "FILLED"

    with orm.session() as session:
        assert session.scalar(select(func.count(OrderModel.id))) == 1
        assert session.scalar(select(func.count(TradeModel.id))) == 1
        assert session.scalar(select(func.count(PositionModel.id))) == 1
        assert session.scalar(select(func.count(ExecutionOutboxModel.id))) == 1

        order = session.scalar(select(OrderModel))
        position = session.scalar(select(PositionModel))
        event = session.scalar(select(ExecutionOutboxModel))
        assert order.status == "FILLED"
        assert position.volume == 5
        assert event.status == "PENDING"


def test_rejected_order_is_persisted_without_trade_position_or_outbox(isolated_trading):
    orm, _ = isolated_trading
    trading_api.execution_engine.status = "REJECTED"

    async def scenario():
        return await trading_api.submit_order(
            {"symbol": "SHFE.rb", "side": "BUY", "volume": 5, "price": 3500}
        )

    response = asyncio.run(scenario())
    assert response["success"] is False
    assert response["order"]["status"] == "REJECTED"

    with orm.session() as session:
        assert session.scalar(select(func.count(OrderModel.id))) == 1
        assert session.scalar(select(func.count(TradeModel.id))) == 0
        assert session.scalar(select(func.count(PositionModel.id))) == 0
        assert session.scalar(select(func.count(ExecutionOutboxModel.id))) == 0


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


def test_outbox_status_reflects_pending_then_processed(isolated_trading, monkeypatch):
    orm, _ = isolated_trading

    async def submit():
        return await trading_api.submit_order(
            {"symbol": "SHFE.rb", "side": "BUY", "volume": 2, "price": 3500}
        )

    response = asyncio.run(submit())
    assert response["success"] is True

    sink_events = []
    monkeypatch.setattr(trading_api.execution_event_sink, "handle", lambda *args: sink_events.append(args))
    dispatcher = trading_api.ExecutionOutboxDispatcher(orm.session, trading_api.execution_event_sink.handle)
    monkeypatch.setattr(trading_api, "execution_outbox_dispatcher", dispatcher)

    async def status_and_dispatch():
        pending = await trading_api.execution_outbox_status()
        dispatched = await trading_api.dispatch_execution_outbox()
        final = await trading_api.execution_outbox_status()
        return pending, dispatched, final

    pending, dispatched, final = asyncio.run(status_and_dispatch())
    assert pending["pending"] == 1
    assert pending["processed"] == 0
    assert dispatched == {"delivered": 1, "retried": 0, "selected": 1}
    assert len(sink_events) == 1
    assert final["pending"] == 0
    assert final["processed"] == 1
    assert final["sink_events"] == 1


def test_get_order_and_list_positions_match_persisted_state(isolated_trading):
    async def submit():
        return await trading_api.submit_order(
            {"symbol": "SHFE.rb", "side": "BUY", "volume": 3, "price": 3500}
        )

    asyncio.run(submit())

    listed = asyncio.run(trading_api.list_orders())
    order_id = listed["orders"][0]["id"]
    fetched = asyncio.run(trading_api.get_order(order_id))
    positions = asyncio.run(trading_api.list_positions())

    assert fetched["order"]["id"] == order_id
    assert fetched["order"]["status"] == "FILLED"
    assert positions["positions"]["SHFE.rb"] == 3
