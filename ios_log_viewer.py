"""
iOS Log Viewer - минимальный просмотрщик логов с iOS-устройства по USB.

Требования:
    pip install -r requirements.txt
    Установлен драйвер Apple Mobile Device (idevice) - ставится вместе
    с iTunes или приложением "Apple Devices" из Microsoft Store.

Запуск:
    python ios_log_viewer.py
"""
import queue
import sys

from PySide6.QtWidgets import QApplication

import qa_theme

from ios_logger.version import VERSION

from ios_logger.backend import LogBackend
from ios_logger.window import APP_NAME, MainWindow


def main() -> int:
    # one shared AppUserModelID or one per tool: the hub's "Общая иконка в таскбаре" setting
    qa_theme.taskbar.apply("iOSLogger")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    qa_theme.init(app, APP_NAME)

    # a second launch (or the hub's "Открыть") asks the running copy to show itself
    if qa_theme.instance.signal_existing("iOSLogger"):
        return 0
    icon = qa_theme.app_icons.app_icon("ios-logger", qa_theme.app_icons.is_test_version(VERSION))
    if not icon.isNull():
        app.setWindowIcon(icon)

    line_queue: queue.Queue = queue.Queue()
    status_queue: queue.Queue = queue.Queue()
    window = MainWindow(line_queue, status_queue)
    backend = LogBackend(line_queue, status_queue)  # daemon-поток, закроется вместе с процессом
    window.backend = backend
    window.show()
    qa_theme.tray.install(window, "iOSLogger", "iOS Logger", app.windowIcon())
    qa_theme.instance.listen("iOSLogger", lambda: qa_theme.instance.bring_to_front(window))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
