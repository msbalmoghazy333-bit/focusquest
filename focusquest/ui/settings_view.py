"""Settings screen: durations, strict default, blacklist, language, reset."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QFormLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from focusquest.i18n import d, language as current_language
from focusquest.ui import theme


class ListEditor(QWidget):
    """QListWidget + input + add/remove row, reusable for apps and sites."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._list = QListWidget()
        self._list.setMinimumHeight(110)
        self._list.setSizePolicy(
            self._list.sizePolicy().horizontalPolicy(),
            self._list.sizePolicy().verticalPolicy(),
        )
        self._input = QLineEdit()
        self._add_btn = QPushButton()
        self._add_btn.setObjectName("ghost")
        self._remove_btn = QPushButton()
        self._remove_btn.setObjectName("danger")
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._input, 1)
        row.addWidget(self._add_btn)
        row.addWidget(self._remove_btn)
        lay.addWidget(self._list, 1)
        lay.addLayout(row)
        self._add_btn.clicked.connect(self._add)
        self._input.returnPressed.connect(self._add)
        self._remove_btn.clicked.connect(self._remove)

    def set_placeholder(self, text: str) -> None:
        self._input.setPlaceholderText(text)

    def set_items(self, items: list[str]) -> None:
        self._list.clear()
        for item in items:
            self._list.addItem(QListWidgetItem(item))

    def items(self) -> list[str]:
        return [self._list.item(i).text() for i in range(self._list.count())]

    def _add(self) -> None:
        value = self._input.text().strip()
        if not value:
            return
        existing = {v.lower() for v in self.items()}
        if value.lower() not in existing:
            self._list.addItem(QListWidgetItem(value))
        self._input.clear()

    def _remove(self) -> None:
        item = self._list.currentItem()
        if item is not None:
            self._list.takeItem(self._list.row(item))


class SettingsView(QWidget):
    settings_changed = Signal()
    language_changed = Signal(str)
    reset_requested = Signal()

    def __init__(self, store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 16)
        root.setSpacing(16)

        self._title = QLabel()
        self._title.setStyleSheet(f"color: {theme.FG}; font-size: 20px; font-weight: 800;")
        root.addWidget(self._title)

        # durations card
        dur_card = QFrame()
        dur_card.setObjectName("Card")
        dur_lay = QVBoxLayout(dur_card)
        dur_lay.setContentsMargins(18, 16, 18, 16)
        self._durations_label = QLabel()
        self._durations_label.setObjectName("SectionLabel")
        dur_lay.addWidget(self._durations_label)
        form = QFormLayout()
        form.setSpacing(10)
        self._focus_min = self._make_spin(1, 180)
        self._break_min = self._make_spin(1, 60)
        self._long_min = self._make_spin(1, 120)
        self._until_long = self._make_spin(1, 12)
        self._focus_lbl = QLabel(); self._break_lbl = QLabel()
        self._long_lbl = QLabel(); self._until_lbl = QLabel()
        form.addRow(self._focus_lbl, self._focus_min)
        form.addRow(self._break_lbl, self._break_min)
        form.addRow(self._long_lbl, self._long_min)
        form.addRow(self._until_lbl, self._until_long)
        dur_lay.addLayout(form)
        self._strict_default = QCheckBox()
        dur_lay.addWidget(self._strict_default)
        root.addWidget(dur_card)

        # blacklist card
        bl_card = QFrame()
        bl_card.setObjectName("Card")
        bl_lay = QVBoxLayout(bl_card)
        bl_lay.setContentsMargins(18, 16, 18, 16)
        self._bl_title = QLabel()
        self._bl_title.setObjectName("SectionLabel")
        bl_lay.addWidget(self._bl_title)
        grid = QGridLayout()
        grid.setSpacing(12)
        self._apps_lbl = QLabel(); self._sites_lbl = QLabel()
        self._apps_editor = ListEditor()
        self._sites_editor = ListEditor()
        grid.addWidget(self._apps_lbl, 0, 0)
        grid.addWidget(self._sites_lbl, 0, 1)
        grid.addWidget(self._apps_editor, 1, 0)
        grid.addWidget(self._sites_editor, 1, 1)
        bl_lay.addLayout(grid)
        self._bl_hint = QLabel()
        self._bl_hint.setObjectName("Muted")
        self._bl_hint.setWordWrap(True)
        bl_lay.addWidget(self._bl_hint)
        root.addWidget(bl_card, 1)

        # language + data row
        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        lang_card = QFrame(); lang_card.setObjectName("Card")
        lang_lay = QVBoxLayout(lang_card)
        lang_lay.setContentsMargins(18, 16, 18, 16)
        self._lang_title = QLabel(); self._lang_title.setObjectName("SectionLabel")
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("العربية", "ar")
        self._lang_combo.addItem("English", "en")
        lang_lay.addWidget(self._lang_title)
        lang_lay.addWidget(self._lang_combo)
        bottom.addWidget(lang_card, 1)

        data_card = QFrame(); data_card.setObjectName("Card")
        data_lay = QVBoxLayout(data_card)
        data_lay.setContentsMargins(18, 16, 18, 16)
        self._data_title = QLabel(); self._data_title.setObjectName("SectionLabel")
        self._data_hint = QLabel(); self._data_hint.setObjectName("Muted")
        self._data_hint.setWordWrap(True)
        self._reset_btn = QPushButton(); self._reset_btn.setObjectName("danger")
        data_lay.addWidget(self._data_title)
        data_lay.addWidget(self._data_hint)
        data_lay.addWidget(self._reset_btn)
        bottom.addWidget(data_card, 1)
        root.addLayout(bottom)

        for spin in (self._focus_min, self._break_min, self._long_min, self._until_long):
            spin.valueChanged.connect(self._emit_changed)
        self._strict_default.toggled.connect(self._emit_changed)
        self._apps_editor._list.itemChanged.connect(self._emit_changed)
        self._sites_editor._list.itemChanged.connect(self._emit_changed)
        self._apps_editor._remove_btn.clicked.connect(self._emit_changed)
        self._sites_editor._remove_btn.clicked.connect(self._emit_changed)
        self._apps_editor._add_btn.clicked.connect(self._emit_changed)
        self._sites_editor._add_btn.clicked.connect(self._emit_changed)
        self._lang_combo.currentIndexChanged.connect(self._on_language)
        self._reset_btn.clicked.connect(self._on_reset)

        self.load_from_store()
        self.retranslate_ui()

    def _make_spin(self, lo: int, hi: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(lo, hi)
        spin.setFixedWidth(110)
        spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        return spin

    def _emit_changed(self, *_args) -> None:
        self.settings_changed.emit()

    def _on_language(self, index: int) -> None:
        code = self._lang_combo.itemData(index)
        if code and code != current_language():
            self.language_changed.emit(code)

    def _on_reset(self) -> None:
        answer = QMessageBox.question(
            self, d("reset_confirm_title"), d("reset_confirm_body"),
            QMessageBox.Yes | QMessageBox.Cancel,
        )
        if answer == QMessageBox.Yes:
            self.reset_requested.emit()

    # ------------------------------------------------------------------ sync
    def load_from_store(self) -> None:
        s = self._store.data.get("settings", {})
        self._focus_min.setValue(int(s.get("focus_minutes", 25)))
        self._break_min.setValue(int(s.get("break_minutes", 5)))
        self._long_min.setValue(int(s.get("long_break_minutes", 15)))
        self._until_long.setValue(int(s.get("sessions_until_long_break", 4)))
        self._strict_default.setChecked(bool(s.get("strict_mode_default", True)))
        self._apps_editor.set_items(list(s.get("blacklist_apps", [])))
        self._sites_editor.set_items(list(s.get("blacklist_sites", [])))
        idx = self._lang_combo.findData(s.get("language", "ar"))
        if idx >= 0:
            self._lang_combo.blockSignals(True)
            self._lang_combo.setCurrentIndex(idx)
            self._lang_combo.blockSignals(False)

    def read_settings(self) -> dict:
        return {
            "focus_minutes": self._focus_min.value(),
            "break_minutes": self._break_min.value(),
            "long_break_minutes": self._long_min.value(),
            "sessions_until_long_break": self._until_long.value(),
            "strict_mode_default": self._strict_default.isChecked(),
            "language": self._lang_combo.currentData(),
            "blacklist_apps": self._apps_editor.items(),
            "blacklist_sites": self._sites_editor.items(),
        }

    def retranslate_ui(self) -> None:
        self._title.setText(d("tab_settings"))
        self._durations_label.setText(d("settings_durations").upper())
        self._focus_lbl.setText(d("focus_min"))
        self._break_lbl.setText(d("break_min"))
        self._long_lbl.setText(d("long_break_min"))
        self._until_lbl.setText(d("sessions_until_long"))
        self._strict_default.setText(d("strict_default"))
        self._bl_title.setText(d("blacklist_title").upper())
        self._apps_lbl.setText(d("blacklist_apps"))
        self._sites_lbl.setText(d("blacklist_sites"))
        self._apps_editor.set_placeholder(d("blacklist_apps_ph"))
        self._sites_editor.set_placeholder(d("blacklist_sites_ph"))
        self._apps_editor._add_btn.setText(d("add"))
        self._apps_editor._remove_btn.setText(d("remove"))
        self._sites_editor._add_btn.setText(d("add"))
        self._sites_editor._remove_btn.setText(d("remove"))
        self._bl_hint.setText(d("blacklist_hint"))
        self._lang_title.setText(d("language").upper())
        self._data_title.setText(d("data_title").upper())
        self._data_hint.setText(d("data_hint"))
        self._reset_btn.setText(d("reset_data"))

    def language_combo(self) -> QComboBox:
        return self._lang_combo
