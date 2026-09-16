from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_projection_websocket_connect():
    with client.websocket_connect('/ws/projections/test-order') as websocket:
        assert websocket is not None
