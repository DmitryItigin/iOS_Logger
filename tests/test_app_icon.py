import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import qa_theme

KEY = "ios-logger"


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("version, test", [("1.0.1", False), ("1.0.1-test.2", True), ("dev", False)])
def test_the_shared_icon_follows_the_build_channel(_app, version, test):
    icons = qa_theme.app_icons
    assert icons.is_test_version(version) is test
    assert icons.icon_path(KEY, test).exists()
    assert not icons.app_icon(KEY, test).isNull()
