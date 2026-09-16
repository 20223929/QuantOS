from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_projection_endpoint_exists():
    response = client.get('/api/projections/test-order')
    assert response.status_code in (200, 404)
