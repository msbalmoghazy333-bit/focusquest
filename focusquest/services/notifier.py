"""Audio + (optional) system notifications.

Sound lookup order: QtMultimedia QSoundEffect → winsound (Windows) → beep.
Everything degrades silently — a broken sound must never crash a session.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from PySide6.QtCore import QUrl
    from PySide6.QtMultimedia import QSoundEffect
    _QT_MULTIMEDIA = True
except Exception:  # pragma: no cover - audio stack is optional
    _QT_MULTIMEDIA = False

SOUND_NAMES = ("focus_end", "break_end", "warning", "levelup", "click")


def assets_sounds_dir() -> Path:
    if getattr(sys, "_MEIPASS", None):  # PyInstaller bundle
        return Path(sys._MEIPASS) / "assets" / "sounds"
    return Path(__file__).resolve().parents[2] / "assets" / "sounds"


class Notifier:
    def __init__(self) -> None:
        self._effects: dict[str, QSoundEffect] = {}

    def sound_path(self, name: str) -> Path:
        return assets_sounds_dir() / f"{name}.wav"

    def play(self, name: str) -> bool:
        path = self.sound_path(name)
        if _QT_MULTIMEDIA:
            try:
                effect = self._effects.get(name)
                if effect is None:
                    effect = QSoundEffect()
                    effect.setSource(QUrl.fromLocalFile(str(path)))
                    effect.setVolume(0.6)
                    self._effects[name] = effect
                effect.play()
                return True
            except Exception:
                pass
        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                return True
            except Exception:
                try:
                    winsound.MessageBeep()  # type: ignore[name-defined]
                    return True
                except Exception:
                    return False
        try:
            print("\a", end="")  # terminal bell as last resort
            return True
        except Exception:
            return False

    @staticmethod
    def notify(tray_icon, title: str, body: str) -> None:
        """Show a system tray balloon if a tray icon is available."""
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            if tray_icon is not None and tray_icon.supportsMessages():
                tray_icon.showMessage(title, body, QSystemTrayIcon.Information, 4000)
        except Exception:
            pass
