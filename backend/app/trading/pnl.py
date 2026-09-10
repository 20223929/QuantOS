class PnLCalculator:
    """Profit and loss calculation service."""

    def calculate(self, entry_price, current_price, volume):
        return (current_price - entry_price) * volume
