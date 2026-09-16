import pytest


class DummyClient:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


@pytest.mark.asyncio
async def test_projection_broadcast():
    from app.websocket.projection_stream import ProjectionStream

    stream = ProjectionStream()
    client = DummyClient()
    stream.subscribe(client)

    await stream.broadcast({"aggregate_id": "order-001", "version": 1})

    assert client.messages[0]["type"] == "projection.updated"
    assert client.messages[0]["aggregate_id"] == "order-001"
