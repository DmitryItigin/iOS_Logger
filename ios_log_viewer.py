"""
iOS Log Viewer - минимальный просмотрщик логов с iOS-устройства по USB.

Требования:
    pip install -r requirements.txt
    Установлен драйвер Apple Mobile Device (idevice) - ставится вместе
    с iTunes или приложением "Apple Devices" из Microsoft Store.

Запуск:
    python ios_log_viewer.py
"""
import os
import queue
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ios_logger.backend import LogBackend
from ios_logger.theme import apply_theme, load_mode
from ios_logger.window import APP_NAME, MainWindow


def _icon_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))))
    return base / "assets" / "icon.ico"


def main() -> int:
    try:
        import ctypes

        # Shared across the whole QA-Hub suite (hub + all tools) so Windows
        # groups their taskbar buttons under one icon, regardless of whether
        # this was launched via the hub or run standalone.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("QA-Hub")
    except (AttributeError, OSError):
        pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_theme(app, load_mode(APP_NAME))
    icon_path = _icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    line_queue: queue.Queue = queue.Queue()
    status_queue: queue.Queue = queue.Queue()
    window = MainWindow(line_queue, status_queue)
    backend = LogBackend(line_queue, status_queue)  # daemon-поток, закроется вместе с процессом
    window.backend = backend
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
