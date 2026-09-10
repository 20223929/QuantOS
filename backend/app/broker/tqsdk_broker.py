"""TqSdk broker adapter placeholder.

The adapter isolates TqSdk execution from QuantOS trading core.
"""


class TqSdkBroker:
    """TqSdk based broker adapter."""

    def __init__(self, api=None):
        self.api = api

    async def submit_order(self, order: dict) -> dict:
        """Submit order through TqSdk in production environment."""
        return {
            **order,
            "status": "SUBMITTED",
        }

    async def cancel_order(self, order_id: str) -> dict:
        return {
            "id": order_id,
            "status": "CANCEL_REQUESTED",
        }

    async def query_account(self) -> dict:
        return {
            "equity": 0,
            "available": 0,
        }

    async def query_position(self) -> list:
        return []
