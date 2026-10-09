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

import qa_theme

from ios_logger.backend import LogBackend
from ios_logger.window import APP_NAME, MainWindow


def _icon_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))))
    return base / "assets" / "icon.ico"


def main() -> int:
    # one shared AppUserModelID or one per tool: the hub's "Общая иконка в таскбаре" setting
    qa_theme.taskbar.apply("iOSLogger")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    qa_theme.init(app, APP_NAME)

    # a second launch (or the hub's "Открыть") asks the running copy to show itself
    if qa_theme.instance.signal_existing("iOSLogger"):
        return 0
    icon_path = _icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    line_queue: queue.Queue = queue.Queue()
    status_queue: queue.Queue = queue.Queue()
    window = MainWindow(line_queue, status_queue)
    backend = LogBackend(line_queue, status_queue)  # daemon-поток, закроется вместе с процессом
    window.backend = backend
    window.show()
    qa_theme.instance.listen("iOSLogger", lambda: qa_theme.instance.bring_to_front(window))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
