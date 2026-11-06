"""Statistics screen: weekly bar chart (QPainter) + badges gallery."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from focusquest.core import stats, xp
from focusquest.i18n import d, is_rtl
from focusquest.ui import theme


class WeeklyChart(QWidget):
    """Manual bar chart — no heavy charting dependency."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(240)
        self._points: list[dict] = []

    def set_points(self, points: list[dict]) -> None:
        self._points = points
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        if not self._points:
            return
        rtl = is_rtl()
        top_pad, bottom_pad = 22, 30
        plot_h = h - top_pad - bottom_pad
        n = len(self._points)
        slot = w / max(1, n)
        bar_w = min(46.0, slot * 0.52)
        max_min = max(1, max(pt["minutes"] for pt in self._points))
        f = QFont(self.font())
        f.setPointSize(9)
        p.setFont(f)

        # baseline
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawLine(12, h - bottom_pad, w - 12, h - bottom_pad)

        for i, pt in enumerate(self._points):
            cx = (w - slot * (i + 0.5)) if rtl else slot * (i + 0.5)
            frac = pt["minutes"] / max_min
            bar_h = max(4.0, plot_h * frac) if pt["minutes"] > 0 else 4.0
            colour = theme.ACCENT if pt["is_today"] else theme.PANEL_3
            fill = QColor(colour)
            fill.setAlpha(255 if pt["is_today"] else 200)
            p.setBrush(fill)
            p.setPen(Qt.NoPen)
            x = cx - bar_w / 2
            y = (h - bottom_pad) - bar_h
            p.drawRoundedRect(x, y, bar_w, bar_h, 6, 6)

            if pt["minutes"] > 0:
                p.setPen(QColor(theme.FG))
                label = str(pt["minutes"])
                tw = p.fontMetrics().horizontalAdvance(label)
                p.drawText(int(cx - tw / 2), int(y - 6), label)

        # day labels (weekday short, locale-independent ordinal)
        p.setPen(QColor(theme.MUTED))
        for i, pt in enumerate(self._points):
            cx = (w - slot * (i + 0.5)) if rtl else slot * (i + 0.5)
            label = pt["date"][8:]  # day-of-month number
            tw = p.fontMetrics().horizontalAdvance(label)
            p.drawText(int(cx - tw / 2), h - 8, label)


class StatCard(QFrame):
    def __init__(self, value: str, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        self._value = QLabel(value)
        self._value.setObjectName("BigStat")
        self._value.setAlignment(Qt.AlignCenter)
        self._caption = QLabel(caption)
        self._caption.setObjectName("SectionLabel")
        self._caption.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._value)
        lay.addWidget(self._caption)
        self.set_caption(caption)

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def set_caption(self, caption: str) -> None:
        self._caption.setText(caption.upper())


class BadgesPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setSpacing(12)
        self._cards: list[tuple[str, QLabel, QLabel]] = []  # id, name_label, status_label
        for idx, (badge_id, titles) in enumerate(xp.BADGES.items()):
            card = QFrame()
            card.setObjectName("Card")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(14, 12, 14, 12)
            name = QLabel("")
            name.setStyleSheet(f"color: {theme.GOLD}; font-weight: 700; font-size: 13px;")
            name.setWordWrap(True)
            status = QLabel("")
            status.setObjectName("Muted")
            lay.addWidget(name)
            lay.addWidget(status)
            self._grid.addWidget(card, idx // 2, idx % 2)
            self._cards.append((badge_id, name, status))

    def refresh(self, owned: list[str]) -> None:
        owned_set = set(owned)
        for badge_id, name_label, status_label in self._cards:
            titles = xp.BADGES[badge_id]["ar" if is_rtl() else "en"]
            name_label.setText(titles[0])
            if badge_id in owned_set:
                status_label.setText("✓ " + titles[1])
                status_label.setProperty("class", "Muted")
            else:
                status_label.setText("🔒 " + d("badge_locked"))
        # a colour that reads as bronze on locked cards
        self.update()


class StatsView(QWidget):
    def __init__(self, store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 16)
        root.setSpacing(16)

        self._title = QLabel()
        self._title.setStyleSheet(f"color: {theme.FG}; font-size: 20px; font-weight: 800;")
        root.addWidget(self._title)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        self._today = StatCard("", "")
        self._week = StatCard("", "")
        self._best = StatCard("", "")
        self._streak = StatCard("", "")
        for card in (self._today, self._week, self._best, self._streak):
            cards_row.addWidget(card, 1)
        root.addLayout(cards_row)

        chart_card = QFrame()
        chart_card.setObjectName("Card")
        chart_lay = QVBoxLayout(chart_card)
        chart_lay.setContentsMargins(18, 16, 18, 12)
        self._chart = WeeklyChart()
        chart_lay.addWidget(self._chart)
        root.addWidget(chart_card, 1)

        self._badges_title = QLabel()
        self._badges_title.setObjectName("SectionLabel")
        root.addWidget(self._badges_title)
        self._badges = BadgesPanel()
        root.addWidget(self._badges, 1)
        self.retranslate_ui()

    def refresh(self) -> None:
        data = self._store.data
        days = data.get("days", {})
        head = stats.headline(days)
        self._today.set_value(f"{head['today_minutes']} {d('minutes')}")
        week_min = head["week_minutes"]
        self._week.set_value(
            f"{week_min // 60}h {week_min % 60}m" if week_min >= 60 else f"{week_min} {d('minutes')}"
        )
        self._best.set_value(f"{head['best_minutes']} {d('minutes')}")
        self._streak.set_value(f"{head['streak_days']} 🔥")
        self._chart.set_points(stats.weekly_series(days))
        self._badges.refresh(list(data.get("badges", [])))

    def retranslate_ui(self) -> None:
        self._title.setText(d("stats_title"))
        self._today.set_caption(d("stats_today"))
        self._week.set_caption(d("stats_week"))
        self._best.set_caption(d("stats_best"))
        self._streak.set_caption(d("stats_streak"))
        self._badges_title.setText(d("badges_title").upper())
        self.refresh()
