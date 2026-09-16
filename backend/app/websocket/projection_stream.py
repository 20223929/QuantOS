from typing import Any, Dict, Set


class ProjectionStream:
    """In-memory projection state broadcaster foundation."""

    def __init__(self) -> None:
        self._subscribers: Set[Any] = set()

    def subscribe(self, client: Any) -> None:
        self._subscribers.add(client)

    def unsubscribe(self, client: Any) -> None:
        self._subscribers.discard(client)

    async def broadcast(self, state: Dict[str, Any]) -> None:
        for client in list(self._subscribers):
            await client.send_json(state)
