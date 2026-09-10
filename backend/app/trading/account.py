from dataclasses import dataclass


@dataclass
class Account:
    equity: float = 0
    available: float = 0
    margin: float = 0

    def margin_ratio(self):
        if self.equity == 0:
            return 0
        return self.margin / self.equity
