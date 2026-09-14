"""TqSdk execution broker.

The vendor order/account objects remain behind this adapter so the core engine
can operate on normalized dictionaries and can be tested without the SDK.
"""

from __future__ import annotations

from typing import Any


class TqSdkBroker:
    def __init__(self, api: Any | None = None, default_offset: str = "OPEN"):
        self.api = api
        self.default_offset = default_offset.upper()

    def _require_api(self):
        if self.api is None:
            raise RuntimeError("TqSdkBroker requires a connected TqApi instance")
        return self.api

    def submit_order(self, order: Any) -> dict:
        api = self._require_api()
        symbol = order.symbol
        side = str(order.side).upper()
        direction = "BUY" if side in {"BUY", "LONG"} else "SELL"
        offset = str(getattr(order, "offset", self.default_offset)).upper()
        volume = int(order.volume)
        kwargs = {"symbol": symbol, "direction": direction, "offset": offset, "volume": volume}
        price = getattr(order, "price", None)
        if price is not None and float(price) > 0:
            kwargs["limit_price"] = float(price)
        vendor_order = api.insert_order(**kwargs)
        order_id = str(getattr(vendor_order, "order_id", getattr(vendor_order, "id", "")))
        status = str(getattr(vendor_order, "status", "ALIVE"))
        order.order_id = order_id or getattr(order, "order_id", None)
        order.broker_order = vendor_order
        return {"id": order_id, "status": status, "vendor_order": vendor_order, **kwargs}

    def cancel_order(self, order: Any | str) -> dict:
        api = self._require_api()
        vendor_order = getattr(order, "broker_order", None)
        if vendor_order is None and not isinstance(order, str):
            vendor_order = order
        if vendor_order is None:
            raise ValueError("cancel_order requires the vendor order object")
        api.cancel_order(vendor_order)
        return {"id": str(getattr(vendor_order, "order_id", getattr(vendor_order, "id", ""))), "status": "CANCEL_REQUESTED"}

    def query_account(self) -> dict:
        api = self._require_api()
        account = api.get_account()
        return {
            "balance": float(getattr(account, "balance", 0) or 0),
            "available": float(getattr(account, "available", 0) or 0),
            "margin": float(getattr(account, "margin", 0) or 0),
            "float_profit": float(getattr(account, "float_profit", 0) or 0),
            "position_profit": float(getattr(account, "position_profit", 0) or 0),
        }

    def query_position(self, symbol: str) -> dict:
        api = self._require_api()
        position = api.get_position(symbol)
        return {
            "symbol": symbol,
            "pos": int(getattr(position, "pos", 0) or 0),
            "long_pos": int(getattr(position, "pos_long", 0) or 0),
            "short_pos": int(getattr(position, "pos_short", 0) or 0),
            "today_long": int(getattr(position, "pos_long_today", 0) or 0),
            "today_short": int(getattr(position, "pos_short_today", 0) or 0),
        }

    def wait_update(self):
        return self._require_api().wait_update()
