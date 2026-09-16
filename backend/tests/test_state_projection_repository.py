import json


from backend.app.storage.models.state_projection import StateProjection



def test_state_projection_model_serialization():
    state = {"position": 1, "status": "ACTIVE"}
    model = StateProjection(
        projection_id="trade-001",
        aggregate_type="trade",
        aggregate_id="001",
        version="v1",
        state_json=json.dumps(state),
    )

    assert model.projection_id == "trade-001"
    assert json.loads(model.state_json) == state


def test_state_projection_fields():
    assert StateProjection.__tablename__ == "state_projections"
    assert hasattr(StateProjection, "aggregate_id")
    assert hasattr(StateProjection, "state_json")
