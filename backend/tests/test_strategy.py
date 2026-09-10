from app.strategy.ma_strategy import MAStrategy


def test_ma_strategy_init():
    strategy = MAStrategy()
    assert strategy is not None
