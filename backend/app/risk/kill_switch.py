class KillSwitch:
    """Emergency stop switch for all trading activities."""

    def __init__(self):
        self._enabled = False

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def active(self) -> bool:
        return self._enabled
