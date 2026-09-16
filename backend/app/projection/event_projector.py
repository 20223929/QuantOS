"""Event projector integrating trading events with persistent state."""

from dataclasses import dataclass

from .state_writer import StateProjectionWriter


@dataclass
class ProjectionResult:
    projection_id: str
    version: str
    state: dict


class EventProjector:
    """Apply events and persist the resulting projection state."""

    def __init__(self, state_writer: StateProjectionWriter):
        self.state_writer = state_writer

    def project(self, event_id: str, aggregate_type: str, aggregate_id: str, version: str, state: dict):
        self.state_writer.persist(
            projection_id=event_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            version=version,
            state=state,
        )

        return ProjectionResult(
            projection_id=event_id,
            version=version,
            state=state,
        )

    def replay(self, events):
        result = None
        for event in events:
            result = self.project(**event)
        return result
