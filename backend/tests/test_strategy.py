from backend.app.strategies.ma_cross import MACrossStrategy


def test_ma_cross_waits_for_enough_data():
    strategy = MACrossStrategy()

    for price in range(10):
        assert strategy.on_bar(float(price)) is None
