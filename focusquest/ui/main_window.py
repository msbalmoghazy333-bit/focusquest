"""Main window: header, tabs, session orchestration, tray, overlays."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox,
    QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget, QTabWidget,
)

from focusquest.core import storage, xp
from focusquest.core.models import SessionRecord
from focusquest.core.timer import Phase, PomodoroTimer, TimerState
from focusquest.i18n import d, set_language, is_rtl
from focusquest.services import focus_mode
from focusquest.services.blocker import DistractionWatcher
from focusquest.services.notifier import Notifier
from focusquest.ui import theme
from focusquest.ui.overlay import WarningOverlay
from focusquest.ui.session_view import SessionView
from focusquest.ui.settings_view import SettingsView
from focusquest.ui.stats_view import StatsView


class MainWindow(QMainWindow):
    def __init__(self, store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        s = self._settings()
        set_language(s.get("language", "ar"))

        self._timer = PomodoroTimer(
            s.get("focus_minutes", 25), s.get("break_minutes", 5),
            s.get("long_break_minutes", 15), s.get("sessions_until_long_break", 4),
        )
        self._notifier = Notifier()
        self._watcher = DistractionWatcher(self)
        self._watcher.set_blacklist(
            list(s.get("blacklist_apps", [])), list(s.get("blacklist_sites", []))
        )
        self._overlay = WarningOverlay()
        self._current_session: SessionRecord | None = None
        self._session_violations = 0
        self._minimized: list[int] = []
        self._last_level = xp.level_for_xp(int(store.data.get("xp", 0)))

        self.setWindowTitle("FocusQuest")
        self.setMinimumSize(760, 620)
        self.resize(880, 680)

        self._build_ui()
        self._build_tray()

        self._watcher.violation.connect(self._on_violation)
        self._watcher.availability_changed.connect(self._on_watcher_availability)
        self._overlay.continue_requested.connect(lambda: None)
        self._overlay.end_requested.connect(self._abort_after_warning)
        self._overlay.raise_()

        self._tick = QTimer(self)
        self._tick.setInterval(200)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start()

        store.subscribe(lambda _data: self._on_store_changed())
        self._apply_language(self._settings().get("language", "ar"), initial=True)
        self._session.refresh_stats()
        self._session.refresh_timer(self._timer)
        self._session.set_strict_checked(bool(s.get("strict_mode_default", True)))

    # --------------------------------------------------------------- ui build
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("appHeader")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(16, 10, 16, 10)
        logo = QLabel("F")
        logo.setObjectName("appLogo")
        logo.setAlignment(Qt.AlignCenter)
        self._title = QLabel()
        self._title.setObjectName("appTitle")
        self._xp_chip = QLabel()
        self._xp_chip.setObjectName("xpChip")
        self._lang_btn = QPushButton()
        self._lang_btn.setObjectName("langButton")
        self._lang_btn.clicked.connect(self._toggle_language)
        hlay.addWidget(logo)
        hlay.addWidget(self._title)
        hlay.addStretch(1)
        hlay.addWidget(self._xp_chip)
        hlay.addWidget(self._lang_btn)
        layout.addWidget(header)

        self._tabs = QTabWidget()
        self._session = SessionView(self._store)
        self._stats = StatsView(self._store)
        self._settings_view = SettingsView(self._store)
        self._tabs.addTab(self._session, "")
        self._tabs.addTab(self._stats, "")
        self._tabs.addTab(self._settings_view, "")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs, 1)

        self._session.primary_clicked.connect(self._on_primary)
        self._session.end_clicked.connect(self._on_end_clicked)
        self._session.strict_toggled.connect(self._on_strict_toggled)
        self._session.restore_clicked.connect(self._restore_windows)
        self._settings_view.settings_changed.connect(self._on_settings_changed)
        self._settings_view.language_changed.connect(self._on_language_changed)
        self._settings_view.reset_requested.connect(self._on_reset_data)

    def _build_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        try:
            icon_path = theme_path_icon()
            if icon_path.exists():
                self._tray.setIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        self._tray.setToolTip("FocusQuest")
        menu = QMenu(self)
        show_action = QAction("FocusQuest", self)
        show_action.triggered.connect(self._restore_from_tray)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    # ---------------------------------------------------------------- helpers
    def _settings(self) -> dict:
        return dict(self._store.data.get("settings", {}))

    def _on_store_changed(self) -> None:
        self._session.refresh_stats()
        self._update_xp_chip()
        if self._tabs.currentIndex() == 1:
            self._stats.refresh()

    def _update_xp_chip(self) -> None:
        total = int(self._store.data.get("xp", 0))
        prog = xp.xp_progress(total)
        self._xp_chip.setText(f"{d('level', n=prog['level'])} · {total} XP")

    def _on_tab_changed(self, index: int) -> None:
        if index == 1:
            self._stats.refresh()
        elif index == 2:
            self._settings_view.load_from_store()

    # ---------------------------------------------------------------- session
    def _on_primary(self) -> None:
        state = self._timer.state
        phase = self._timer.phase
        if state is TimerState.IDLE:
            if phase is Phase.FOCUS and self._current_session is None:
                self._current_session = SessionRecord.now(
                    int(self._timer.phase_length_seconds())
                )
                self._current_session.task = self._session.current_task
                self._session.clear_task()
                self._session_violations = 0
                self._watcher.reset_counters()
                if self._session._strict.isChecked():
                    self._minimized = focus_mode.minimize_others()
                    self._session.show_restore_button(True)
            self._timer.start()
            if phase is Phase.FOCUS:
                self._watcher.start()
        elif state is TimerState.RUNNING:
            self._timer.pause()
            self._watcher.stop()
        else:  # paused -> resume
            self._timer.start()
            if self._timer.phase is Phase.FOCUS:
                self._watcher.start()
        self._notifier.play("click")
        self._session.refresh_timer(self._timer)

    def _on_end_clicked(self) -> None:
        if self._timer.state is TimerState.IDLE:
            return
        answer = QMessageBox.question(
            self, d("quit_title"), d("quit_body"),
            QMessageBox.Yes | QMessageBox.Cancel,
        )
        if answer == QMessageBox.Yes:
            self._abort_session()

    def _abort_session(self) -> None:
        was_focus = self._timer.phase is Phase.FOCUS
        worked = int(self._timer.active_focus_seconds()) if was_focus else 0
        before_level = self._last_level
        if was_focus:
            xp.apply_penalty(self._store.data, xp.EARLY_QUIT_PENALTY)
            if self._current_session is not None:
                self._current_session.worked_sec = worked
                self._current_session.completed = False
                self._current_session.violations = self._session_violations
                from focusquest.core import stats as stats_mod
                stats_mod.record_session(
                    self._store.data, self._current_session.to_dict()
                )
                self._current_session = None
            self._check_level_up(before_level)
        self._watcher.stop()
        self._restore_windows()
        self._timer.force_break_after_abort()
        self._store.save()
        self._session.set_violations(0)
        self._session.refresh_timer(self._timer)

    def _abort_after_warning(self) -> None:
        # Overlay "End session" must not ask for confirmation again.
        self._abort_session()

    def _restore_windows(self) -> None:
        if self._minimized:
            focus_mode.restore(self._minimized)
            self._minimized = []
        self._session.show_restore_button(False)

    # ------------------------------------------------------------------- tick
    def _on_tick(self) -> None:
        result = self._timer.tick()
        grants = self._timer.grant_minute_xp()
        if grants:
            before = self._last_level
            xp.grant_focus_minutes(self._store.data, grants)
            self._check_level_up(before)
            self._store.save()

        if result is not None:
            kind, finished = result
            if kind == "completed" and finished == Phase.FOCUS.value:
                self._on_focus_completed()
            elif kind == "completed":
                self._notifier.play("break_end")
                Notifier.notify(self._tray, d("app_title"), d("break_title") if "break_title" in _all_keys() else d("focus_next"))
                self._restore_windows()

        self._session.refresh_timer(self._timer)
        self._session.set_violations(self._watcher.violation_count if self._watcher.isActive() else self._session_violations)

    def _on_focus_completed(self) -> None:
        before = self._last_level
        xp.grant_session_bonus(self._store.data)
        self._watcher.stop()
        if self._current_session is not None:
            self._current_session.worked_sec = int(self._timer.phase_length_seconds())
            self._current_session.completed = True
            self._current_session.violations = self._session_violations
            self._current_session.task = self._current_session.task or "(session)"
            from focusquest.core import stats as stats_mod
            stats_mod.record_session(self._store.data, self._current_session.to_dict())
            self._current_session = None
        newly = xp.award_badges(self._store.data)
        self._check_level_up(before)
        self._store.save()
        self._notifier.play("focus_end")
        Notifier.notify(self._tray, d("app_title"), d("phase_break") + " / " + d("focus_next"))
        self._session.set_violations(0)
        self._restore_windows()
        for badge_id in newly:
            self._celebrate_badge(badge_id)

    def _check_level_up(self, before: int) -> None:
        total = int(self._store.data.get("xp", 0))
        now = xp.level_for_xp(total)
        self._last_level = now
        if now > before:
            self._notifier.play("levelup")
            QMessageBox.information(
                self, d("level_up_title"), d("level_up_body", n=now)
            )

    def _celebrate_badge(self, badge_id: str) -> None:
        titles = xp.BADGES[badge_id]["ar" if is_rtl() else "en"]
        self._notifier.play("levelup")
        QMessageBox.information(
            self, d("badge_unlocked"), f"🏆 {titles[0]}\n{titles[1]}"
        )

    # -------------------------------------------------------------- watchdog
    def _on_violation(self, reason: str) -> None:
        if self._timer.phase is not Phase.FOCUS:
            return
        self._session_violations += 1
        before = self._last_level
        xp.apply_penalty(self._store.data, xp.VIOLATION_PENALTY)
        self._check_level_up(before)
        self._store.save()
        self._notifier.play("warning")
        self._overlay.show_for(reason)
        self._session.set_violations(self._session_violations)

    def _on_watcher_availability(self, available: bool) -> None:
        enabled = self._timer.state is TimerState.RUNNING and self._timer.phase is Phase.FOCUS
        self._session.set_shield_state(enabled, available)

    def _on_strict_toggled(self, checked: bool) -> None:
        if checked and self._timer.state is TimerState.RUNNING and self._timer.phase is Phase.FOCUS:
            self._minimized = focus_mode.minimize_others()
            self._session.show_restore_button(True)
        elif not checked:
            self._restore_windows()

    # ------------------------------------------------------------------- i18n
    def _toggle_language(self) -> None:
        self._on_language_changed("en" if is_rtl() else "ar")

    def _on_language_changed(self, code: str) -> None:
        self._store.data.setdefault("settings", {})["language"] = code
        self._store.save()
        self._apply_language(code)

    def _apply_language(self, code: str, initial: bool = False) -> None:
        set_language(code)
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setLayoutDirection(
            Qt.RightToLeft if is_rtl() else Qt.LeftToRight
        )
        self._title.setText(d("app_title"))
        self._lang_btn.setText("English" if is_rtl() else "العربية")
        self._tabs.setTabText(0, d("tab_session"))
        self._tabs.setTabText(1, d("tab_stats"))
        self._tabs.setTabText(2, d("tab_settings"))
        self._session.retranslate_ui()
        self._stats.retranslate_ui()
        self._settings_view.retranslate_ui()
        self._session.set_shield_state(
            self._timer.state is TimerState.RUNNING and self._timer.phase is Phase.FOCUS,
            self._watcher.available,
        )
        self._update_xp_chip()
        self._session.refresh_timer(self._timer)

    # -------------------------------------------------------------- settings
    def _on_settings_changed(self) -> None:
        s = self._settings_view.read_settings()
        self._store.data["settings"] = s
        self._store.save()
        if self._timer.state is TimerState.IDLE:
            self._timer.reconfigure(
                s["focus_minutes"], s["break_minutes"],
                s["long_break_minutes"], s["sessions_until_long_break"],
            )
        self._watcher.set_blacklist(s["blacklist_apps"], s["blacklist_sites"])
        if not s["strict_mode_default"]:
            self._session.set_strict_checked(False)

    def _on_reset_data(self) -> None:
        storage.reset_all()
        self._store = storage.DataStore()
        self._last_level = 1
        self._settings_view.load_from_store()
        self._session.refresh_stats()
        self._update_xp_chip()
        self._stats.refresh()
        self._apply_language(storage.default_data()["settings"]["language"])

    # ------------------------------------------------------------------- tray
    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._restore_from_tray()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._timer.state in (TimerState.RUNNING, TimerState.PAUSED) and self._timer.phase is Phase.FOCUS:
            answer = QMessageBox.question(
                self, d("quit_title"), d("quit_body"),
                QMessageBox.Yes | QMessageBox.Cancel,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self._abort_session()
        self._watcher.stop()
        self._restore_windows()
        try:
            self._tray.hide()
        except Exception:
            pass
        self._store.data.setdefault("settings", {})["language"] = self._settings().get("language", "ar")
        self._store.save()
        event.accept()


def _all_keys() -> set[str]:
    from focusquest.i18n import en, ar
    return set(en.STRINGS) | set(ar.STRINGS)


def theme_path_icon():
    import sys
    from pathlib import Path
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "assets" / "icons" / "icon.svg"
    return Path(__file__).resolve().parents[2] / "assets" / "icons" / "icon.svg"
