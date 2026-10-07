"""Light/dark look shared by every QA-Hub tool (the file is copied verbatim into each
tool's repo -- keep it dependency-free beyond PySide6).

The choice is persisted per app in ``%APPDATA%\\QA_Hub\\<app>\\theme.json`` -- outside the
hub's versioned tool cache, so it survives both restarts and updates. Light is the
default; the OS theme is deliberately ignored so every tool looks the same.
"""
import json
import os
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QToolButton

LIGHT = "light"
DARK = "dark"
DEFAULT_MODE = LIGHT
SETTINGS_ROOT = "QA_Hub"

_COLORS = {
    LIGHT: {
        "window": "#f3f3f3",
        "base": "#ffffff",
        "alt_base": "#f7f7f7",
        "text": "#1b1b1b",
        "muted": "#6b6b6b",
        "button": "#fbfbfb",
        "button_hover": "#f0f0f0",
        "button_pressed": "#e6e6e6",
        "border": "#d1d1d1",
        "accent": "#0067c0",
        "accent_text": "#ffffff",
        "disabled": "#a0a0a0",
    },
    DARK: {
        "window": "#202020",
        "base": "#2b2b2b",
        "alt_base": "#272727",
        "text": "#f3f3f3",
        "muted": "#a8a8a8",
        "button": "#333333",
        "button_hover": "#3d3d3d",
        "button_pressed": "#2a2a2a",
        "border": "#454545",
        "accent": "#4cc2ff",
        "accent_text": "#003250",
        "disabled": "#777777",
    },
}

_STYLESHEET = """
QToolTip {{ background: {base}; color: {text}; border: 1px solid {border}; padding: 4px; }}
QPushButton, QToolButton {{
    background: {button}; color: {text}; border: 1px solid {border};
    border-radius: 5px; padding: 5px 14px;
}}
QToolButton {{ padding: 5px 10px; }}
QPushButton:hover, QToolButton:hover {{ background: {button_hover}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {button_pressed}; }}
QPushButton:default {{ background: {accent}; color: {accent_text}; border-color: {accent}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {disabled}; background: {window}; }}
QLineEdit, QPlainTextEdit, QTextEdit {{
    background: {base}; color: {text}; border: 1px solid {border};
    border-radius: 5px; padding: 4px 6px;
    selection-background-color: {accent}; selection-color: {accent_text};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {accent};
}}
QTreeView, QListView, QListWidget, QTableView, QTableWidget {{
    background: {base}; alternate-background-color: {alt_base}; color: {text};
    border: 1px solid {border}; border-radius: 5px;
    selection-background-color: {accent}; selection-color: {accent_text};
}}
QHeaderView::section {{
    background: {window}; color: {muted}; border: none;
    border-bottom: 1px solid {border}; padding: 4px 6px;
}}
QTabWidget::pane {{ border: 1px solid {border}; border-radius: 5px; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {muted}; padding: 6px 16px; border: none; }}
QTabBar::tab:selected {{ color: {text}; border-bottom: 2px solid {accent}; }}
QTabBar::tab:hover {{ color: {text}; }}
QProgressBar {{
    background: {base}; border: 1px solid {border}; border-radius: 5px;
    text-align: center; color: {text};
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
QGroupBox {{ border: 1px solid {border}; border-radius: 6px; margin-top: 10px; padding-top: 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {muted}; }}
QMenu {{ background: {base}; color: {text}; border: 1px solid {border}; padding: 4px; }}
QMenu::item {{ padding: 5px 24px; border-radius: 4px; }}
QMenu::item:selected {{ background: {accent}; color: {accent_text}; }}
QStatusBar {{ color: {muted}; }}
QSplitter::handle {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
QScrollBar::handle {{ background: {border}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: {disabled}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


def settings_path(app_name: str) -> Path:
    base = os.environ.get("APPDATA", str(Path.home()))
    return Path(base) / SETTINGS_ROOT / app_name / "theme.json"


def load_mode(app_name: str) -> str:
    try:
        mode = json.loads(settings_path(app_name).read_text(encoding="utf-8")).get("mode")
    except (OSError, ValueError, AttributeError):
        return DEFAULT_MODE
    return mode if isinstance(mode, str) and mode in _COLORS else DEFAULT_MODE


def save_mode(app_name: str, mode: str) -> None:
    path = settings_path(app_name)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({"mode": mode}), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass  # a theme that doesn't persist is a nuisance, never a crash


def _palette(colors: dict[str, str]) -> QPalette:
    palette = QPalette()
    q = QColor
    roles = {
        QPalette.Window: colors["window"],
        QPalette.WindowText: colors["text"],
        QPalette.Base: colors["base"],
        QPalette.AlternateBase: colors["alt_base"],
        QPalette.Text: colors["text"],
        QPalette.Button: colors["button"],
        QPalette.ButtonText: colors["text"],
        QPalette.ToolTipBase: colors["base"],
        QPalette.ToolTipText: colors["text"],
        QPalette.Highlight: colors["accent"],
        QPalette.HighlightedText: colors["accent_text"],
        QPalette.PlaceholderText: colors["muted"],
        QPalette.Link: colors["accent"],
    }
    for role, value in roles.items():
        palette.setColor(role, q(value))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        palette.setColor(QPalette.Disabled, role, q(colors["disabled"]))
    return palette


def apply_theme(app: QApplication, mode: str) -> None:
    colors = _COLORS.get(mode, _COLORS[DEFAULT_MODE])
    if app.style().objectName().lower() != "fusion":
        app.setStyle("Fusion")
    if app.font().family() != "Segoe UI":
        font = app.font()
        font.setFamily("Segoe UI")
        app.setFont(font)
    app.setPalette(_palette(colors))
    app.setStyleSheet(_STYLESHEET.format(**colors))


class ThemeToggleButton(QToolButton):
    """Shows the theme a click switches *to*; applies and persists it."""

    theme_changed = Signal(str)

    def __init__(self, app_name: str, parent=None):
        super().__init__(parent)
        self._app_name = app_name
        self._mode = load_mode(app_name)
        self.setToolTip("Переключить тему")
        self.clicked.connect(self._toggle)
        self._refresh_text()

    def _refresh_text(self) -> None:
        self.setText("☾ Тёмная" if self._mode == LIGHT else "☀ Светлая")

    def _toggle(self) -> None:
        self._mode = DARK if self._mode == LIGHT else LIGHT
        save_mode(self._app_name, self._mode)
        apply_theme(QApplication.instance(), self._mode)
        self._refresh_text()
        self.theme_changed.emit(self._mode)
