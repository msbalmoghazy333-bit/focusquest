import time as real_time

import pytest

from focusquest.core import timer as timer_module
from focusquest.core.timer import PomodoroTimer, Phase, TimerState


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, secs: float):
        self.now += secs


@pytest.fixture()
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(timer_module.time, "monotonic", fake)
    return fake


def test_idle_phase_reports_full_focus_length():
    t = PomodoroTimer(25, 5)
    assert t.state is TimerState.IDLE
    assert t.phase is Phase.FOCUS
    assert t.remaining_seconds() == 25 * 60
    assert t.elapsed_fraction() == 0.0


def test_full_cycle_focus_then_break_then_idle(clock):
    t = PomodoroTimer()
    t.reconfigure(1 / 60, 0, 0, 4)  # 1-second focus, 0-second break
    t.start()
    assert t.state is TimerState.RUNNING and t.phase is Phase.FOCUS
    clock.advance(1.1)
    completed = t.tick()
    assert completed == ("completed", "focus")
    assert t.phase is Phase.BREAK          # break auto-starts after focus
    clock.advance(0.1)
    assert t.tick() == ("completed", "break")
    assert t.state is TimerState.IDLE     # waits for user to begin next focus
    assert t.phase is Phase.FOCUS


def test_pause_never_consumes_time(clock):
    t = PomodoroTimer(10, 5)
    t.start()
    clock.advance(120)
    t.pause()
    remaining_before = t.remaining_seconds()
    clock.advance(3600)  # user away for an hour
    assert t.remaining_seconds() == pytest.approx(remaining_before, abs=0.01)
    t.start()
    clock.advance(60)
    assert t.state is TimerState.RUNNING
    assert t.remaining_seconds() == pytest.approx(remaining_before - 60, abs=0.1)


def test_minute_xp_grants_only_active_minutes(clock):
    t = PomodoroTimer(10, 5)
    t.start()
    clock.advance(61)
    assert t.grant_minute_xp() == 1          # first full minute pays out
    clock.advance(59)                          # cumulative active = 120s
    assert t.grant_minute_xp() == 1          # second minute pays out
    t.pause()
    clock.advance(600)                         # paused time must NOT pay out
    t.start()
    assert t.grant_minute_xp() == 0


def test_long_break_after_four_focus_sessions(clock):
    t = PomodoroTimer(0, 5, 20, 4)  # instant focus; short 5min, long 20min breaks
    break_lengths = []
    for _ in range(4):
        t.start()
        clock.advance(0.1)
        assert t.tick() == ("completed", "focus")
        break_len = t.phase_length_seconds()
        break_lengths.append(break_len)
        clock.advance(break_len + 0.1)  # complete the break
        assert t.tick() == ("completed", "break")
    assert break_lengths == [5 * 60, 5 * 60, 5 * 60, 20 * 60]


def test_reconfigure_blocked_while_running():
    t = PomodoroTimer(25, 5)
    t.start()
    assert t.reconfigure(30, 10, 20, 4) is False
    t.pause()
    assert t.reconfigure(30, 10, 20, 4) is False
