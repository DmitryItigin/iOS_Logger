import os
import queue

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

import qa_theme
from ios_logger.window import MainWindow

LINE = "13:21:06.002 {level:<7} MyGame[1]: request failed"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    qa_theme.init(app, "iOS-Logger-test")
    qa_theme.set_mode("dark", persist=False)
    return MainWindow(queue.Queue(), queue.Queue())


def _line_formats(window, text):
    window.text.setPlainText(text)
    block = window.text.document().firstBlock()
    return {(r.start, r.length): r.format.foreground().color().name().upper() for r in block.layout().formats()}


def test_mode_switch_replaces_the_toggle_button(window):
    assert window.findChild(qa_theme.ModeSwitch) is not None


def test_error_level_is_tinted_with_the_error_token(window):
    formats = _line_formats(window, LINE.format(level="ERROR"))
    assert qa_theme.tokens()["error"].upper() in formats.values()


def test_timestamp_is_muted_and_message_keeps_normal_colour(window):
    formats = _line_formats(window, LINE.format(level="INFO"))
    assert formats[(0, 12)] == qa_theme.tokens()["text_muted"].upper()
    assert all(start + length <= 20 for start, length in formats)  # nothing colours the message


def test_status_dot_follows_connection_state(window):
    window.status_queue.put(("connected", "iPhone"))
    window.poll_queues()
    assert window.status_label.text() == "Подключено: iPhone"
    assert window.status_dot.kind() == "dot"
    window.status_queue.put(("error", "boom"))
    window.poll_queues()
    assert window.status_label.text() == "Ошибка: boom"


def test_search_highlight_colours_follow_the_theme(window):
    window.line_queue.put(LINE.format(level="INFO"))
    window.poll_queues()
    window.show_search()
    window.search_entry.setText("request")
    window.run_search()
    def match_bg():
        return window._match_selections[0].format.background().color().name().upper()

    assert match_bg() == qa_theme.tokens()["match_soft"].upper()
    qa_theme.set_mode("light", persist=False)
    assert match_bg() == qa_theme.tokens()["match_soft"].upper()
    qa_theme.set_mode("dark", persist=False)


def test_search_buttons_have_accessible_names(window):
    names = {b.accessibleName() for b in window.search_frame.findChildren(type(window.pause_btn))}
    assert {"Предыдущее", "Следующее", "Закрыть поиск"} <= names


def test_close_to_tray_checkbox_sits_next_to_the_mode_switch_and_is_off_by_default(window):
    from PySide6.QtWidgets import QCheckBox

    box = next(b for b in window.findChildren(QCheckBox) if b.text() == "Закрывать в трей")
    assert not box.isChecked()
    box.click()
    assert qa_theme.settings.load_close_to_tray("iOSLogger") is True
