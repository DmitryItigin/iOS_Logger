import queue

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from ios_logger.window import MainWindow

LINE = "12:00:00.000 INFO    App[1]: line {}"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_lines_received_during_pause_appear_after_resume(app):
    lines, status = queue.Queue(), queue.Queue()
    window = MainWindow(lines, status)
    lines.put(LINE.format(1))
    window.poll_queues()

    window.toggle_pause()
    lines.put(LINE.format(2))
    window.poll_queues()
    assert "line 2" not in window.text.toPlainText()
    assert len(window.buffer) == 2

    window.toggle_pause()
    assert "line 2" in window.text.toPlainText()
    assert window.visible_count == 2
