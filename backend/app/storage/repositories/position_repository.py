from backend.app.storage.repository import Repository


class PositionRepository(Repository):
    """Repository for position snapshot persistence."""

    def save_position(self, position):
        return self.save(position)
