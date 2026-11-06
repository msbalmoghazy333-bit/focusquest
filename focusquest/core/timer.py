"""Pomodoro session state machine.

Pure Python — no Qt imports allowed here so the whole engine is unit-testable.

The countdown is deadline-based (monotonic clock), never decremented tick-by-tick,
so timer drift is impossible even if the UI misses frames.
"""
from __future__ import annotations

import time
from enum import Enum


class Phase(Enum):
    FOCUS = "focus"
    BREAK = "break"


class TimerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class PomodoroTimer:
    """Intelligent focus cycle: FOCUS -> BREAK -> FOCUS ...

    A long break replaces the short break every ``sessions_until_long_break``
    completed focus sessions. Pauses never consume the deadline; resuming
    pushes the deadline forward, which is what keeps the countdown exact.
    """

    def __init__(self, focus_minutes: int = 25, break_minutes: int = 5,
                 long_break_minutes: int = 15, sessions_until_long_break: int = 4) -> None:
        self._focus_sec = int(focus_minutes * 60)
        self._break_sec = int(break_minutes * 60)
        self._long_break_sec = int(long_break_minutes * 60)
        self._sessions_until_long_break = int(sessions_until_long_break)

        self._phase = Phase.FOCUS
        self._state = TimerState.IDLE
        self._deadline = 0.0            # monotonic deadline of current phase
        self._paused_remaining = 0.0     # seconds left, captured when paused
        self._phase_len = float(self._focus_sec)

        self._active_accum = 0.0         # active seconds banked before current segment
        self._resume_at = 0.0            # monotonic timestamp of (re)start
        self._active_granted = 0.0       # active seconds already converted into XP

        self._cycle_count = 0            # completed focus sessions since last long break
        self._focus_sessions_total = 0   # all-time completed focus sessions (session)

    # ------------------------------------------------------------------ config
    def reconfigure(self, focus_minutes: int, break_minutes: int,
                    long_break_minutes: int, sessions_until_long_break: int) -> bool:
        """Apply new durations. Only allowed while IDLE; returns success."""
        if self._state is not TimerState.IDLE:
            return False
        self._focus_sec = int(focus_minutes * 60)
        self._break_sec = int(break_minutes * 60)
        self._long_break_sec = int(long_break_minutes * 60)
        self._sessions_until_long_break = int(sessions_until_long_break)
        self._phase_len = float(self._focus_sec)
        return True

    # ------------------------------------------------------------------ state
    @property
    def state(self) -> TimerState:
        return self._state

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def session_total_focus(self) -> int:
        """All focus sessions completed since app start."""
        return self._focus_sessions_total

    def phase_length_seconds(self) -> int:
        return int(self._phase_len)

    def remaining_seconds(self) -> float:
        if self._state is TimerState.IDLE:
            return float(self._phase_len)
        if self._state is TimerState.PAUSED:
            return self._paused_remaining
        return max(0.0, self._deadline - time.monotonic())

    def elapsed_fraction(self) -> float:
        total = max(1.0, self._phase_len)
        return 1.0 - (self.remaining_seconds() / total)

    def active_focus_seconds(self) -> float:
        """Active (unpaused) seconds in the current FOCUS phase."""
        if self._phase is not Phase.FOCUS:
            return float(self._focus_sec)
        if self._state is TimerState.RUNNING:
            return self._active_accum + (time.monotonic() - self._resume_at)
        if self._state is TimerState.PAUSED:
            return self._active_accum
        return 0.0

    # --------------------------------------------------------------- control
    def start(self) -> None:
        if self._state is TimerState.IDLE:
            self._begin_phase(self._phase)
        elif self._state is TimerState.PAUSED:
            now = time.monotonic()
            self._deadline = now + self._paused_remaining
            self._resume_at = now
            self._state = TimerState.RUNNING

    def pause(self) -> None:
        if self._state is not TimerState.RUNNING:
            return
        now = time.monotonic()
        self._paused_remaining = max(0.0, self._deadline - now)
        self._active_accum += now - self._resume_at
        self._state = TimerState.PAUSED

    def reset(self) -> None:
        """Abandon current phase -> back to IDLE (focus phase is the current one)."""
        self._state = TimerState.IDLE
        self._deadline = 0.0
        self._paused_remaining = float(self._focus_sec if self._phase is Phase.FOCUS else self._break_sec)
        self._phase_len = float(self._paused_remaining)
        self._active_accum = 0.0
        self._active_granted = 0.0

    def force_break_after_abort(self) -> None:
        """After a manual abort mid-focus, move back to IDLE on the focus phase."""
        self.reset()
        self._phase = Phase.FOCUS

    # ------------------------------------------------------------------ tick
    def tick(self):
        """Return ('completed', phase_name) once when a phase ends, else None."""
        if self._state is not TimerState.RUNNING:
            return None
        if time.monotonic() < self._deadline:
            return None
        completed = self._phase
        self._close_phase()
        return ("completed", completed.value)

    def grant_minute_xp(self) -> int:
        """Return how many whole focus minutes elapsed since the last grant."""
        if self._phase is not Phase.FOCUS or self._state is not TimerState.RUNNING:
            return 0
        delta = self.active_focus_seconds() - self._active_granted
        grants = int(max(0.0, delta) // 60.0)
        if grants:
            self._active_granted += grants * 60.0
        return grants

    # ------------------------------------------------------------- internals
    def _begin_phase(self, phase: Phase) -> None:
        self._phase = phase
        self._phase_len = float(
            self._focus_sec if phase is Phase.FOCUS else
            (self._long_break_sec if self._is_long_break_due() else self._break_sec)
        )
        now = time.monotonic()
        self._deadline = now + self._phase_len
        self._resume_at = now
        self._paused_remaining = self._phase_len
        self._active_accum = 0.0
        self._active_granted = 0.0
        self._state = TimerState.RUNNING

    def _close_phase(self) -> None:
        if self._phase is Phase.FOCUS:
            self._active_accum += time.monotonic() - self._resume_at
            self._cycle_count += 1
            self._focus_sessions_total += 1
            self._begin_break()
        else:  # break finished -> ready for next focus, stay IDLE for user consent
            self._state = TimerState.IDLE
            self._phase = Phase.FOCUS
            self._phase_len = float(self._focus_sec)
            self._paused_remaining = self._phase_len
            self._deadline = 0.0

    def _begin_break(self) -> None:
        self._phase = Phase.BREAK
        self._phase_len = float(
            self._long_break_sec if self._is_long_break_due() else self._break_sec
        )
        now = time.monotonic()
        self._deadline = now + self._phase_len
        self._resume_at = now
        self._paused_remaining = self._phase_len
        if self._cycle_count % self._sessions_until_long_break == 0:
            self._cycle_count = 0
        self._state = TimerState.RUNNING

    def _is_long_break_due(self) -> bool:
        n = self._sessions_until_long_break
        return n > 0 and self._cycle_count > 0 and self._cycle_count % n == 0
