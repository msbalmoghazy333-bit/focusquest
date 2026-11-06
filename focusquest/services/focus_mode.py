"""Strict focus mode: minimize every visible top-level window except our own.

Returns the list of minimized handles so the UI can offer an one-click
restore when the session ends. Windows-only; on other platforms it is a
safe no-op returning an empty list.
"""
from __future__ import annotations

import sys

try:
    import win32con
    import win32gui
    import win32process
    import psutil
    import os
    _WIN_OK = sys.platform == "win32"
except Exception:  # pragma: no cover - platform/dependency guard
    _WIN_OK = False


def _is_cloaked(hwnd: int) -> bool:
    try:
        import ctypes
        from ctypes import wintypes
        cloaked = wintypes.BOOL()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)  # DWMWA_CLOAKED
        )
        return bool(cloaked.value)
    except Exception:
        return False


def minimize_others() -> list[int]:
    """Minimize all visible, non-tool top-level windows except FocusQuest."""
    if not _WIN_OK:
        return []
    try:
        my_pid = os.getpid()
    except Exception:
        my_pid = -1
    minimized: list[int] = []

    def enum_handler(hwnd: int, _extra) -> bool:
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            if win32gui.IsIconic(hwnd):
                return True  # already minimized — don't touch (restore semantics)
            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex & win32con.WS_EX_TOOLWINDOW:
                return True
            if _is_cloaked(hwnd):
                return True
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid == my_pid:
                return True  # never minimize ourselves
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True  # skip empty utility windows
            try:
                proc = psutil.Process(pid).name().lower()
            except Exception:
                proc = ""
            if proc in ("explorer.exe", "shell_traywnd", "applicationframehost.exe"):
                return True
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            minimized.append(hwnd)
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(enum_handler, None)
    except Exception:
        return minimized
    return minimized


def restore(hwnds: list[int]) -> int:
    """Restore previously minimized windows. Returns count restored."""
    if not _WIN_OK or not hwnds:
        return 0
    count = 0
    for hwnd in hwnds:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            count += 1
        except Exception:
            continue
    return count
