"""Repository for persisted state projections."""

import json

from ..models.state_projection import StateProjection


class StateProjectionRepository:
    def __init__(self, session):
        self.session = session

    def save(self, projection_id, aggregate_type, aggregate_id, version, state):
        entity = self.session.get(StateProjection, projection_id)
        payload = json.dumps(state)

        if entity:
            entity.aggregate_type = aggregate_type
            entity.aggregate_id = aggregate_id
            entity.version = version
            entity.state_json = payload
        else:
            entity = StateProjection(
                projection_id=projection_id,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                version=version,
                state_json=payload,
            )
            self.session.add(entity)

        self.session.commit()
        return entity

    def get(self, projection_id):
        return self.session.get(StateProjection, projection_id)

    def load_state(self, projection_id):
        entity = self.get(projection_id)
        if not entity:
            return None
        return json.loads(entity.state_json)
