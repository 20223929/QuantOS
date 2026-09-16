import json


class FakeRepository:
    def __init__(self):
        self.data = {}

    def save(self, projection_id, aggregate_type, aggregate_id, version, state):
        self.data[projection_id] = {
            "version": version,
            "state": json.loads(json.dumps(state)),
        }
        return self.data[projection_id]

    def load_state(self, projection_id):
        item = self.data.get(projection_id)
        return item["state"] if item else None


def test_projection_state_persist_and_restore():
    from app.projection.state_writer import StateProjectionWriter

    repo = FakeRepository()
    writer = StateProjectionWriter(repo)

    writer.persist(
        "account-1",
        "account",
        "account-1",
        "v1",
        {"position": 10},
    )

    assert writer.restore("account-1") == {"position": 10}


def test_projection_replay_latest_state():
    from app.projection.state_writer import StateProjectionWriter

    repo = FakeRepository()
    writer = StateProjectionWriter(repo)

    writer.persist("account-1", "account", "account-1", "v1", {"position": 1})
    writer.persist("account-1", "account", "account-1", "v2", {"position": 2})

    assert writer.restore("account-1") == {"position": 2}
