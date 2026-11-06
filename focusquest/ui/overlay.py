"""Distraction warning overlay — frameless, translucent, always-on-top."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from focusquest.i18n import d
from focusquest.ui import theme


class WarningOverlay(QWidget):
    """Big friendly-but-firm slap on the wrist, one click to obey."""

    continue_requested = Signal()
    end_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.Tool)          # keep off the main window task switch list
        self._reason = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.addStretch(1)

        card = QWidget(self)
        card.setObjectName("overlayCard")
        card.setFixedWidth(520)
        card.setStyleSheet(f"""
            QWidget#overlayCard {{
                background-color: {theme.PANEL};
                border: 1px solid {theme.DANGER};
                border-radius: 20px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(36, 32, 36, 28)
        lay.setSpacing(14)

        self._icon = WarningBadge(card)
        lay.addWidget(self._icon, alignment=Qt.AlignHCenter)

        self._title = QLabel(card)
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(f"color: {theme.DANGER}; font-size: 26px; font-weight: 800;")
        lay.addWidget(self._title)

        self._body = QLabel(card)
        self._body.setAlignment(Qt.AlignCenter)
        self._body.setWordWrap(True)
        self._body.setStyleSheet(f"color: {theme.FG}; font-size: 15px;")
        lay.addWidget(self._body)

        row = QHBoxLayout()
        row.setSpacing(12)
        self._continue_btn = QPushButton(card)
        self._continue_btn.setObjectName("primary")
        self._continue_btn.clicked.connect(self._on_continue)
        self._end_btn = QPushButton(card)
        self._end_btn.setObjectName("danger")
        self._end_btn.clicked.connect(self._on_end)
        row.addWidget(self._continue_btn, 1)
        row.addWidget(self._end_btn, 1)
        lay.addLayout(row)

        outer.addWidget(card, alignment=Qt.AlignHCenter)
        outer.addStretch(1)
        self.retranslate_ui()

    # ------------------------------------------------------------- behaviour
    def show_for(self, reason: str) -> None:
        self._reason = reason
        self._body.setText(d("warning_body", reason=reason))
        self._fit_to_screen()
        self.show()
        self.raise_()
        self.activateWindow()

    def _fit_to_screen(self) -> None:
        screen = self.screen()
        if screen is None and self.parent() is not None:
            screen = self.parent().screen()
        if screen is not None:
            self.setGeometry(screen.geometry())

    def _on_continue(self) -> None:
        self.hide()
        self.continue_requested.emit()

    def _on_end(self) -> None:
        self.hide()
        self.end_requested.emit()

    # -------------------------------------------------------------- painting
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(10, 10, 20, 205))

    # -------------------------------------------------------------- i18n
    def retranslate_ui(self) -> None:
        self._title.setText(d("warning_title"))
        self._continue_btn.setText(d("warning_continue"))
        self._end_btn.setText(d("warning_end"))


class WarningBadge(QWidget):
    """Drawn triangle-with-exclamation, scaled crisply at any DPI."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(120, 110)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        cx, cy = self.width() / 2, self.height() / 2 + 4
        r = 46
        path = QPainterPath()
        path.moveTo(cx, cy - r)
        path.lineTo(cx - r * 0.95, cy + r * 0.75)
        path.lineTo(cx + r * 0.95, cy + r * 0.75)
        path.closeSubpath()
        grad = QRadialGradient(cx, cy, r * 1.4)
        grad.setColorAt(0.0, QColor(247, 118, 142, 90))
        grad.setColorAt(1.0, QColor(247, 118, 142, 0))
        p.fillRect(self.rect(), grad)
        p.setPen(QPen(QColor(theme.DANGER), 3))
        p.setBrush(QColor("#2b1b22"))
        p.drawPath(path)
        # exclamation
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.DANGER))
        bar_w, bar_h = 8, 34
        p.drawRoundedRect(int(cx - bar_w / 2), int(cy - 16), bar_w, bar_h, 4, 4)
        p.drawEllipse(int(cx - 5), int(cy + 26), 10, 10)
