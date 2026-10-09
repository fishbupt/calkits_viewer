"""CalKit Viewer GUI: app."""

import logging
import sys
from pathlib import Path

from matplotlib import font_manager, rcParams
from PyQt6.QtCore import (
    QStandardPaths,
    QTimer,
)
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
)

from .window import XKTViewer

LOGGER = logging.getLogger(__name__)


def _configure_app(app):
    app.setApplicationName("XKT CalKit Viewer")
    app.setOrganizationName("Keysight Tools")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))
    palette = QPalette()
    for role, color in [
        (QPalette.ColorRole.Window, "#eef2f7"),
        (QPalette.ColorRole.WindowText, "#273449"),
        (QPalette.ColorRole.Base, "#ffffff"),
        (QPalette.ColorRole.AlternateBase, "#f8fafc"),
        (QPalette.ColorRole.Text, "#273449"),
        (QPalette.ColorRole.Button, "#ffffff"),
        (QPalette.ColorRole.ButtonText, "#405169"),
        (QPalette.ColorRole.Highlight, "#eaf2ff"),
        (QPalette.ColorRole.HighlightedText, "#1d4f9b"),
        (QPalette.ColorRole.ToolTipBase, "#ffffff"),
        (QPalette.ColorRole.ToolTipText, "#273449"),
    ]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    names = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in (
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
    ):
        if candidate in names:
            rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break
    rcParams["axes.unicode_minus"] = False


def main():
    app = QApplication(sys.argv)
    _configure_app(app)
    log_dir = Path(
        QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler(
        log_dir / "viewer.log", maxBytes=2_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger("calkit_viewer").addHandler(handler)
    logging.getLogger("calkit_viewer").setLevel(logging.INFO)
    win = XKTViewer()
    win.show()
    if len(sys.argv) > 1:
        QTimer.singleShot(0, lambda: win._load_file(sys.argv[1]))
    return app.exec()
