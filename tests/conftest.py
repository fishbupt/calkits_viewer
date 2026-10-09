import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from calkit_viewer.gui.app import _configure_app


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path_factory.mktemp("settings")),
    )
    instance = QApplication.instance() or QApplication([])
    _configure_app(instance)
    return instance


@pytest.fixture
def demo_path():
    return Path(__file__).parents[1] / "examples/demo.xkt"
