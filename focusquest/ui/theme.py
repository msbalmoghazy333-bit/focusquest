"""FocusQuest dark theme — soft, low-glare Tokyo Night palette."""
from __future__ import annotations

# Palette (single source of truth, reused by painters)
BG          = "#1a1b26"
PANEL       = "#24283b"
PANEL_2     = "#1f2335"
PANEL_3     = "#2f344d"
FG          = "#c0caf5"
MUTED       = "#565f89"
ACCENT      = "#7aa2f7"
ACCENT_2    = "#9ece6a"
DANGER      = "#f7768e"
GOLD        = "#e0af68"
BORDER      = "#3b4261"

QSS = f"""
* {{ outline: none; }}
QWidget {{
    background-color: {BG};
    color: {FG};
    font-family: 'Segoe UI', 'Noto Sans Arabic', 'Tahoma', sans-serif;
    font-size: 14px;
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}
QMainWindow {{ background-color: {BG}; }}

/* ---------- header ---------- */
#appHeader {{
    background-color: {PANEL_2};
    border-bottom: 1px solid {BORDER};
}}
#appLogo {{
    background-color: {ACCENT};
    color: {BG};
    border-radius: 14px;
    font-weight: 800;
    font-size: 15px;
    min-width: 28px; max-width: 28px;
    min-height: 28px; max-height: 28px;
}}
#appTitle {{ font-size: 17px; font-weight: 700; color: {FG}; }}
#xpChip {{
    background-color: {PANEL_3};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 4px 12px;
    color: {GOLD};
    font-weight: 700;
}}
#langButton {{
    background-color: transparent;
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 5px 14px;
    color: {FG};
    font-weight: 600;
}}
#langButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}

/* ---------- tabs ---------- */
QTabWidget::pane {{ border: none; top: 0; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 10px 26px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:hover {{ color: {FG}; }}
QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; }}

/* ---------- panels ---------- */
.Card {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
.SectionLabel {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
}}
.Muted {{ color: {MUTED}; font-size: 12px; }}
.BigStat {{ color: {FG}; font-size: 26px; font-weight: 800; }}
.Danger {{ color: {DANGER}; font-weight: 700; }}

/* ---------- inputs ---------- */
QLineEdit, QSpinBox {{
    background-color: {PANEL_3};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 10px 14px;
    color: {FG};
}}
QLineEdit:focus, QSpinBox:focus {{ border-color: {ACCENT}; background-color: {PANEL}; }}
QLineEdit::placeholder {{ color: {MUTED}; }}

/* ---------- buttons ---------- */
QPushButton {{
    border: none;
    border-radius: 12px;
    padding: 11px 22px;
    font-weight: 700;
    color: {FG};
    background-color: {PANEL_3};
}}
QPushButton:hover {{ background-color: {BORDER}; }}
QPushButton#primary {{
    background-color: {ACCENT};
    color: {BG};
    padding: 12px 42px;
    font-size: 15px;
}}
QPushButton#primary:hover {{ background-color: #8db0ff; }}
QPushButton#danger {{
    background-color: transparent;
    border: 1px solid {DANGER};
    color: {DANGER};
}}
QPushButton#danger:hover {{ background-color: rgba(247,118,142,0.12); }}
QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid {BORDER};
}}
QPushButton#ghost:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}

/* ---------- progress bar ---------- */
QProgressBar {{
    background-color: {PANEL_3};
    border: none;
    border-radius: 6px;
    min-height: 10px; max-height: 10px;
}}
QProgressBar::chunk {{
    background-color: {GOLD};
    border-radius: 6px;
}}

/* ---------- checkbox ---------- */
QCheckBox {{ color: {FG}; spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border-radius: 5px;
    border: 1px solid {BORDER};
    background: {PANEL_3};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* ---------- list widgets ---------- */
QListWidget {{
    background-color: {PANEL_2};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 6px;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 8px;
    color: {FG};
}}
QListWidget::item:selected {{ background: {PANEL_3}; color: {ACCENT}; }}

/* ---------- scrollbars ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ---------- message boxes ---------- */
QMessageBox {{ background-color: {PANEL}; }}
QMessageBox QLabel {{ color: {FG}; }}
"""
