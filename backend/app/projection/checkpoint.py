"""Projection replay checkpoint and idempotency support."""


class ProjectionCheckpoint:
    """Tracks processed events for replay safety."""

    def __init__(self):
        self._processed_events = set()
        self._versions = {}

    def is_processed(self, event_id):
        return event_id in self._processed_events

    def mark_processed(self, event_id, aggregate_id, version):
        self._processed_events.add(event_id)
        self._versions[aggregate_id] = version

    def validate_version(self, aggregate_id, version):
        current = self._versions.get(aggregate_id)
        if current is None:
            return True
        return version > current

    def accept(self, event_id, aggregate_id, version):
        if self.is_processed(event_id):
            return False
        if not self.validate_version(aggregate_id, version):
            return False
        self.mark_processed(event_id, aggregate_id, version)
        return True
