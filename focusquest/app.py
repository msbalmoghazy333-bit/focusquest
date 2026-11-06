"""Application bootstrap: QApplication, theme, window, event loop."""
from __future__ import annotations

import os
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from focusquest.core import storage
from focusquest.ui import theme
from focusquest.ui.main_window import MainWindow

APP_ID = "com.focusquest.focusquest"


def create_app(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("FocusQuest")
    app.setOrganizationName("FocusQuest")
    app.setApplicationDisplayName("FocusQuest")
    app.setDesktopFileName(APP_ID)
    app.setStyleSheet(theme.QSS)
    # Prefer a font stack where Arabic renders cleanly on every platform.
    font = QFont("Segoe UI", 11)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)
    return app


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "windows")
    app = create_app(argv)
    store = storage.DataStore()
    window = MainWindow(store)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
