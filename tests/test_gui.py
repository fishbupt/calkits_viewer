import time

import pytest
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QMessageBox

from calkit_viewer import CalKitData, parse_xkt
from calkit_viewer.gui import pages
from calkit_viewer.gui.theme import S_COLORS
from calkit_viewer.gui.window import XKTViewer


@pytest.fixture
def window(app):
    w = XKTViewer()
    yield w
    w.close()
    app.processEvents()


def wait_loaded(w, app):
    deadline = time.monotonic() + 5
    while w._loading and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    assert not w._loading


def test_real_parser_async(window, app, demo_path):
    window._load_file(str(demo_path))
    wait_loaded(window, app)
    assert window.metrics["standards"].text() == "5"
    assert window.metrics["decoded"].text() == "1" and window.open_button.isEnabled()
    window.standards_page.table.selectRow(4)
    app.processEvents()
    axes = [
        a for a in window.standards_page.plot_widget.fig.axes if a.get_title(loc="left")
    ]
    assert len(axes) == 4 and [a.lines[0].get_color() for a in axes] == list(
        S_COLORS.values()
    )


def test_real_gui_export(window, app, demo_path, tmp_path, monkeypatch):
    kit = parse_xkt(demo_path)
    window._populate(kit, str(demo_path))
    s = kit.standards[-1]
    monkeypatch.setattr(
        pages.QFileDialog,
        "getSaveFileName",
        lambda *args: (str(tmp_path / "db.s2p"), ""),
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    window.standards_page._export_snp(s)
    assert "# Hz S RI R 50" in (tmp_path / "db.s2p").read_text()
    monkeypatch.setattr(
        pages.QFileDialog,
        "getSaveFileName",
        lambda *args: (str(tmp_path / "db.csv"), ""),
    )
    window.standards_page._export_uncertainty(s)
    assert (tmp_path / "db.csv").is_file()


def test_switch_and_clear(window, app, demo_path):
    kit = parse_xkt(demo_path)
    window._populate(kit, str(demo_path))
    for _ in range(8):
        window.standards_page.table.selectRow(4)
        window.standards_page.table.selectRow(0)
    app.processEvents()
    assert window.standards_page.prop_layout.count() == 4
    window._populate(CalKitData(), "empty.xkt")
    app.processEvents()
    assert (
        window.standards_page.table.rowCount() == 0
        and window.connectors_page.table.rowCount() == 0
    )
    assert window.standards_page.plot_title.text() == "No standard selected"


def test_failure_retains_kit(window, app, demo_path, monkeypatch, tmp_path):
    window._load_file(str(demo_path))
    wait_loaded(window, app)
    old = window._kit
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)
    window._load_file(str(tmp_path / "missing.xkt"))
    wait_loaded(window, app)
    assert window._kit is old and window.metrics["standards"].text() == "5"
    assert "File not found" in window.log_widget.toPlainText()
