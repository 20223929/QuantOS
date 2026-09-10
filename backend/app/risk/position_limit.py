class PositionLimit:
    """Position and exposure limit checker."""

    def __init__(self, max_volume: int = 20):
        self.max_volume = max_volume

    def check(self, volume: int) -> bool:
        return volume <= self.max_volume
