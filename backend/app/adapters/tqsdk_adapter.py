"""TqSdk market adapter with lazy SDK construction."""

from __future__ import annotations

from typing import Any


class TqSdkAdapter:
    def __init__(self, api: Any | None = None, auth: Any | None = None):
        self.api = api
        self.auth = auth
        self.connected = api is not None

    async def connect(self):
        if self.api is None:
            try:
                from tqsdk import TqApi
            except ImportError as exc:
                raise RuntimeError("tqsdk is required for live market access") from exc
            self.api = TqApi(auth=self.auth) if self.auth is not None else TqApi()
        self.connected = True
        return self

    def _require_connection(self):
        if not self.connected or self.api is None:
            raise RuntimeError("adapter is not connected")

    async def subscribe(self, symbol: str):
        self._require_connection()
        quote = self.api.get_quote(symbol)
        return {"symbol": symbol, "status": "subscribed", "quote": quote}

    async def get_tick(self, symbol: str):
        self._require_connection()
        quote = self.api.get_quote(symbol)
        return {
            "symbol": symbol,
            "price": float(getattr(quote, "last_price", 0) or 0),
            "bid_price1": float(getattr(quote, "bid_price1", 0) or 0),
            "ask_price1": float(getattr(quote, "ask_price1", 0) or 0),
            "volume": int(getattr(quote, "volume", 0) or 0),
            "timestamp": getattr(quote, "datetime", None),
            "quote": quote,
        }

    async def get_bars(self, symbol: str, duration_seconds: int = 60, data_length: int = 200):
        self._require_connection()
        return self.api.get_kline_serial(symbol, duration_seconds, data_length)

    async def close(self):
        if self.api is not None and hasattr(self.api, "close"):
            self.api.close()
        self.connected = False
