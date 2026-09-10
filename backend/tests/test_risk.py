from app.risk.kill_switch import KillSwitch


def test_kill_switch():
    switch = KillSwitch()
    assert switch.active() is False
    switch.enable()
    assert switch.active() is True
