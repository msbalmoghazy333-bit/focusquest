"""Session screen: timer ring, current task, XP bar, strict-focus controls."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from focusquest.core import stats, xp
from focusquest.i18n import d
from focusquest.ui import theme


class TimerRing(QWidget):
    """Circular countdown with soft glow. Arc = progress of the phase."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(280, 280)
        self._fraction = 0.0
        self._text = "25:00"
        self._phase_key = "phase_focus"
        self._subtext = ""
        self._is_break = False

    def set_state(self, fraction: float, text: str, phase_key: str,
                  subtext: str, is_break: bool) -> None:
        self._fraction = max(0.0, min(1.0, fraction))
        self._text = text
        self._phase_key = phase_key
        self._subtext = subtext
        self._is_break = is_break
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        side = min(rect.width(), rect.height()) - 18
        x = (rect.width() - side) / 2
        y = (rect.height() - side) / 2
        ring = rect.adjusted(18, 18, -18, -18)
        cx, cy = rect.center().x(), rect.center().y()

        # background track
        track_pen = QPen(QColor(theme.PANEL_3), 16, Qt.SolidLine, Qt.RoundCap)
        p.setPen(track_pen)
        p.drawEllipse(int(x), int(y), int(side), int(side))

        # progress arc
        color = theme.ACCENT_2 if self._is_break else theme.ACCENT
        glow = QColor(color)
        glow.setAlpha(60)
        p.setPen(QPen(glow, 22, Qt.SolidLine, Qt.RoundCap))
        self._draw_arc(p, ring, 22)
        p.setPen(QPen(QColor(color), 12, Qt.SolidLine, Qt.RoundCap))
        self._draw_arc(p, ring, 12)

        # time text
        p.setPen(QColor(theme.FG))
        f = QFont(self.font())
        f.setPointSize(44)
        f.setBold(True)
        p.setFont(f)
        p.drawText(int(cx - 130), int(cy - 40), 260, 64, Qt.AlignCenter, self._text)

        # phase + cycle sub-label
        f.setPointSize(11)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor(theme.MUTED))
        p.drawText(int(cx - 130), int(cy + 22), 260, 22,
                   Qt.AlignCenter, d(self._phase_key).upper())
        p.drawText(int(cx - 130), int(cy + 44), 260, 20,
                   Qt.AlignCenter, self._subtext)

    def _draw_arc(self, p: QPainter, ring, pen_width: int) -> None:
        start_angle = 90 * 16                     # 12 o'clock
        span = -int(360 * 16 * self._fraction)    # clockwise
        p.drawArc(ring, start_angle, span)


class SessionView(QWidget):
    """Central screen; MainWindow feeds it timer state on a 200ms tick."""

    primary_clicked = Signal()
    end_clicked = Signal()
    strict_toggled = Signal(bool)
    restore_clicked = Signal()

    def __init__(self, store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 16)
        root.setSpacing(14)

        # ---------- XP header row
        xp_row = QHBoxLayout()
        self._level_chip = QLabel()
        self._level_chip.setObjectName("xpChip")
        self._xp_text = QLabel()
        self._xp_text.setObjectName("Muted")
        xp_row.addWidget(self._level_chip)
        xp_row.addStretch(1)
        xp_row.addWidget(self._xp_text)
        root.addLayout(xp_row)

        self._xp_bar = QProgressBar()
        self._xp_bar.setTextVisible(False)
        self._xp_bar.setRange(0, 100)
        root.addWidget(self._xp_bar)

        # ---------- task backlog input
        self._task = QLineEdit()
        self._task.setMaxLength(120)
        root.addWidget(self._task)

        # ---------- timer ring
        self._ring = TimerRing()
        root.addWidget(self._ring, alignment=Qt.AlignHCenter)

        # ---------- strict mode + shield status
        strict_row = QHBoxLayout()
        self._strict = QCheckBox()
        self._restore_btn = QPushButton()
        self._restore_btn.setObjectName("ghost")
        self._restore_btn.setVisible(False)
        self._restore_btn.clicked.connect(self.restore_clicked.emit)
        strict_row.addWidget(self._strict)
        strict_row.addStretch(1)
        strict_row.addWidget(self._restore_btn)
        root.addLayout(strict_row)

        self._shield_label = QLabel()
        self._shield_label.setObjectName("Muted")
        root.addWidget(self._shield_label)

        # ---------- primary actions
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._primary = QPushButton()
        self._primary.setObjectName("primary")
        self._primary.clicked.connect(self.primary_clicked.emit)
        self._end_btn = QPushButton()
        self._end_btn.setObjectName("danger")
        self._end_btn.clicked.connect(self.end_clicked.emit)
        btn_row.addWidget(self._primary)
        btn_row.addWidget(self._end_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        self._violations = QLabel()
        self._violations.setObjectName("Muted")
        self._violations.setAlignment(Qt.AlignCenter)
        root.addWidget(self._violations)

        # ---------- done today
        self._done_label = QLabel()
        self._done_label.setObjectName("SectionLabel")
        root.addWidget(self._done_label)
        self._done_list = QListWidget()
        self._done_list.setMaximumHeight(110)
        self._done_list.setSelectionMode(QListWidget.NoSelection)
        root.addWidget(self._done_list)

        self._strict.toggled.connect(self.strict_toggled.emit)
        self.retranslate_ui()

    # ------------------------------------------------------------------ api
    @property
    def current_task(self) -> str:
        return self._task.text().strip()

    def task_text(self) -> str:
        return self._task.text().strip()

    def clear_task(self) -> None:
        self._task.clear()

    def set_task_input_enabled(self, enabled: bool) -> None:
        self._task.setEnabled(enabled)

    def set_strict_checked(self, checked: bool) -> None:
        self._strict.blockSignals(True)
        self._strict.setChecked(checked)
        self._strict.blockSignals(False)

    def show_restore_button(self, visible: bool) -> None:
        if visible:
            self._restore_btn.setText("↺ " + d("window_restored").split(".")[0])
        self._restore_btn.setVisible(visible)

    def refresh_stats(self) -> None:
        data = self._store.data
        prog = xp.xp_progress(int(data.get("xp", 0)))
        self._level_chip.setText(d("level", n=prog["level"]))
        self._xp_text.setText(d("xp_of_next", into=prog["into_level"],
                                need=prog["needed_for_next"]))
        self._xp_bar.setValue(int(prog["progress"] * 100))

        self._done_list.clear()
        done = stats.completed_today(data)
        if not done:
            item = QListWidgetItem(d("no_completed_today"))
            item.setForeground(QColor(theme.MUTED))
            self._done_list.addItem(item)
        else:
            for s in done:
                task = s.get("task") or "—"
                self._done_list.addItem(QListWidgetItem(f"✓  {task}"))

    def refresh_timer(self, timer) -> None:
        remaining = timer.remaining_seconds()
        mm, ss = divmod(int(remaining), 60)
        phase = timer.phase.value
        is_break = phase == "break"
        phase_key = "phase_break" if is_break else "phase_focus"
        goal = timer._sessions_until_long_break  # display-only, same module family
        if is_break:
            cycle = timer.cycle_count if timer.cycle_count else goal
        else:
            cycle = min(timer.cycle_count + 1, goal)
        subtext = d("cycle_progress", n=cycle, goal=goal)
        self._ring.set_state(timer.elapsed_fraction(), f"{mm:02d}:{ss:02d}",
                             phase_key, subtext, is_break)

        from focusquest.core.timer import TimerState
        state = timer.state
        if state is TimerState.IDLE:
            self._primary.setText(d("start"))
            self._end_btn.setVisible(False)
            self._task.setEnabled(True)
        elif state is TimerState.PAUSED:
            self._primary.setText(d("resume"))
            self._end_btn.setVisible(True)
            self._task.setEnabled(False)
        else:
            self._primary.setText(d("pause"))
            self._end_btn.setVisible(True)
            self._task.setEnabled(is_break)  # task locked during a focus run

    def set_violations(self, count: int) -> None:
        if count <= 0:
            self._violations.setText("")
        else:
            self._violations.setText(f"⚠ ×{count}")
        self._violations.setVisible(count > 0)

    def set_shield_state(self, enabled: bool, available: bool) -> None:
        if not available:
            self._shield_label.setText(d("blocker_unavailable"))
        elif enabled:
            self._shield_label.setText("🛡 " + d("blacklist_active"))
        else:
            self._shield_label.setText("")

    # -------------------------------------------------------------- i18n
    def retranslate_ui(self) -> None:
        self._task.setPlaceholderText(d("task_placeholder"))
        self._strict.setText(d("strict_mode"))
        self._end_btn.setText(d("end_session"))
        self._done_label.setText(d("today_done").upper())
        self._primary.setText(d("start"))
        self._xp_text.setText("")
        self.refresh_stats()
