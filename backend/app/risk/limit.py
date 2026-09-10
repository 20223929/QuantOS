from dataclasses import dataclass


@dataclass
class RiskLimit:
    max_position: int = 1
    max_drawdown: float = 0.2

    def allow_position(self, volume: int):
        return volume <= self.max_position
