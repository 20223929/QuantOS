from dataclasses import dataclass


@dataclass
class StrategyRecord:
    id: int
    name: str
    status: str = "stopped"
