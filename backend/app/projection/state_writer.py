"""State projection persistence writer.

Bridges projection replay results and persistent state storage.
"""


class StateProjectionWriter:
    def __init__(self, repository):
        self.repository = repository

    def persist(self, projection_id, aggregate_type, aggregate_id, version, state):
        return self.repository.save(
            projection_id=projection_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            version=version,
            state=state,
        )

    def restore(self, projection_id):
        return self.repository.load_state(projection_id)
