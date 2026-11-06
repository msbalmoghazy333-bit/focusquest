"""Lightweight distraction shield.

Detects the foreground application/window-title once per second *while a
focus session is running* and fires a ``violation`` signal when it matches
the user's blacklist. Windows-only implementation; on any other platform or
if the Win32 bindings are missing the watcher reports itself unavailable and
the UI degrades gracefully.
"""
from __future__ import annotations

import sys
import time

from PySide6.QtCore import QObject, QTimer, Signal

try:  # Windows with pywin32 + psutil
    import win32gui
    import win32process
    import psutil
    _WIN_OK = sys.platform == "win32"
except Exception:  # pragma: no cover - platform/dependency guard
    _WIN_OK = False

_COOLDOWN_SECONDS = 10.0


def foreground_info() -> tuple[str, str] | None:
    """Return (process_name, window_title) lower-cased, or None."""
    if not _WIN_OK:
        return None
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        title = (win32gui.GetWindowText(hwnd) or "").strip().lower()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid).name().lower() if pid else ""
        return proc, title
    except Exception:
        return None


def match_blacklist(info: tuple[str, str] | None,
                    apps: list[str], sites: list[str],
                    own_process_markers: tuple[str, ...] = ("python", "focusquest", "pyside")) -> str | None:
    """Return a human-readable reason when the foreground matches, else None."""
    if info is None:
        return None
    proc, title = info
    for marker in own_process_markers:  # never flag ourselves
        if marker in proc:
            return None
    for app in apps:
        app = (app or "").strip().lower()
        if app and (app == proc or app in proc):
            return proc
    for site in sites:
        site = (site or "").strip().lower()
        if site and site in title:
            return site
    return None


class DistractionWatcher(QObject):
    violation = Signal(str)   # reason (process name / site keyword)
    availability_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._check)
        self._apps: list[str] = []
        self._sites: list[str] = []
        self._last_fire = 0.0
        self._violation_count = 0

    @property
    def available(self) -> bool:
        return _WIN_OK

    @property
    def violation_count(self) -> int:
        return self._violation_count

    def reset_counters(self) -> None:
        self._violation_count = 0
        self._last_fire = 0.0

    def set_blacklist(self, apps: list[str], sites: list[str]) -> None:
        self._apps = [a for a in apps if a and a.strip()]
        self._sites = [s for s in sites if s and s.strip()]

    def start(self) -> None:
        self.reset_counters()
        self.availability_changed.emit(self.available)
        if self.available:
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _check(self) -> None:
        reason = match_blacklist(foreground_info(), self._apps, self._sites)
        if reason is None:
            return
        now = time.monotonic()
        if now - self._last_fire < _COOLDOWN_SECONDS:
            return  # cooldown: one warning per 10s, not a barrage
        self._last_fire = now
        self._violation_count += 1
        self.violation.emit(reason)
