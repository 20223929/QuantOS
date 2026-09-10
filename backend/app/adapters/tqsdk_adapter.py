"""TqSdk market adapter.

Vendor SDK is isolated from QuantOS engines.
"""


class TqSdkAdapter:
    def __init__(self, account=None):
        self.account = account
        self.connected = False

    async def connect(self):
        self.connected = True

    async def subscribe(self, symbol: str):
        if not self.connected:
            raise RuntimeError("adapter is not connected")
        return {"symbol": symbol, "status": "subscribed"}

    async def get_tick(self, symbol: str):
        return {"symbol": symbol, "price": 0}

    async def close(self):
        self.connected = False
