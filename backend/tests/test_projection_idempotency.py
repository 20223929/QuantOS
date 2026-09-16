from app.projection.checkpoint import ProjectionCheckpoint


def test_duplicate_event_is_ignored():
    checkpoint = ProjectionCheckpoint()

    assert checkpoint.accept("event-1", "order-1", 1) is True
    assert checkpoint.accept("event-1", "order-1", 1) is False


def test_old_version_is_rejected():
    checkpoint = ProjectionCheckpoint()

    assert checkpoint.accept("event-1", "order-1", 2) is True
    assert checkpoint.accept("event-2", "order-1", 1) is False
