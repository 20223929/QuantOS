from app.projection.event_projector import EventProjector


class FakeWriter:
    def __init__(self):
        self.states = []

    def persist(self, **kwargs):
        self.states.append(kwargs)


def test_event_projection_persists_state():
    writer = FakeWriter()
    projector = EventProjector(writer)

    projector.project(
        event_id="event-1",
        aggregate_type="order",
        aggregate_id="order-1",
        version="1",
        state={"status": "created"},
    )

    assert len(writer.states) == 1
    assert writer.states[0]["state"]["status"] == "created"


def test_event_replay_keeps_latest_state():
    writer = FakeWriter()
    projector = EventProjector(writer)

    result = projector.replay([
        {
            "event_id": "event-1",
            "aggregate_type": "order",
            "aggregate_id": "order-1",
            "version": "1",
            "state": {"status": "created"},
        },
        {
            "event_id": "event-2",
            "aggregate_type": "order",
            "aggregate_id": "order-1",
            "version": "2",
            "state": {"status": "filled"},
        },
    ])

    assert result.version == "2"
    assert result.state["status"] == "filled"
