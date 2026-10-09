"""CalKit Viewer GUI: window."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import (
    QSettings,
    QSize,
    Qt,
    QThread,
    pyqtSignal,
)
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from calkit_viewer.parser import (
    CalKitData,
    XKTValidationError,
    parse_xkt,
)

from .helpers import InfoLabel, _card
from .pages import ConnectorsPage, StandardsPage
from .theme import STYLE_SHEET

LOGGER = logging.getLogger(__name__)


class _LoadWorker(QThread):
    loaded = pyqtSignal(object, str)
    failed = pyqtSignal(str, str, str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            self.loaded.emit(parse_xkt(self.path), self.path)
        except Exception as exc:
            LOGGER.exception("File parsing failed")
            title = (
                "Unsupported or invalid XKT"
                if isinstance(exc, XKTValidationError)
                else type(exc).__name__
            )
            self.failed.emit(title, str(exc), self.path)


class XKTViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self._kit: Optional[CalKitData] = None
        self._worker = None
        self._loading = False
        self._progress = None
        self.settings = QSettings("Keysight Tools", "XKT CalKit Viewer")
        self.setWindowTitle("XKT CalKit Viewer")
        self.resize(1500, 980)
        self.setMinimumSize(1100, 760)
        self.setStyleSheet(STYLE_SHEET)
        self._build_ui()
        self._restore_state()

    def _build_ui(self):
        toolbar = QToolBar("Main toolbar")
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        toolbar.addWidget(InfoLabel("CalKit Viewer", "title"))
        toolbar.addSeparator()
        self.open_button = QPushButton("Open .xkt")
        self.open_button.setProperty("role", "primary")
        self.open_button.clicked.connect(self.open_file)
        toolbar.addWidget(self.open_button)
        action = QAction("Open", self)
        action.setShortcut("Ctrl+O")
        action.triggered.connect(self.open_file)
        self.addAction(action)
        self.open_act = action
        about = QPushButton("About")
        about.clicked.connect(self._show_about)
        toolbar.addWidget(about)
        spacer = QWidget()
        spacer.setObjectName("toolbarSpacer")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        self.kit_info_lbl = InfoLabel("No file loaded", "subtle")
        self.kit_info_lbl.setWordWrap(False)
        self.kit_info_lbl.setFixedWidth(390)
        self.kit_info_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        toolbar.addWidget(self.kit_info_lbl)
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(12)
        self.tabs = QTabWidget()
        self.connectors_page = ConnectorsPage()
        self.standards_page = StandardsPage()
        self.tabs.addTab(self.connectors_page, "Connectors")
        self.tabs.addTab(self.standards_page, "Standards")
        self.standards_page.notice.connect(self._log)
        layout.addWidget(self.tabs, 1)
        summary = QHBoxLayout()
        summary.setSpacing(12)
        self.metrics = {}
        for key, title in [
            ("connectors", "Connectors"),
            ("standards", "Standards"),
            ("database", "Database standards"),
            ("decoded", "Decoded database"),
        ]:
            card, cl = _card("")
            header = InfoLabel(title, "key")
            value = InfoLabel("—", "metric")
            cl.addWidget(header)
            cl.addWidget(value)
            summary.addWidget(card, 1)
            self.metrics[key] = value
        layout.addLayout(summary)
        self.log_dock = QDockWidget("Activity log", self)
        self.log_dock.setObjectName("activityLog")
        self.log_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.log_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.log_widget = QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumBlockCount(1500)
        self.log_dock.setWidget(self.log_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        self.resizeDocks([self.log_dock], [110], Qt.Orientation.Vertical)
        toggle = self.log_dock.toggleViewAction()
        toggle.setText("Activity log")
        toolbar.addAction(toggle)
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready · Open an .xkt file to begin")
        self._log("Ready. Open a calibration kit to inspect connectors and standards.")

    def _restore_state(self):
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        state = self.settings.value("window_state")
        if state:
            self.restoreState(state)
        for key, split in [
            ("standards_split", self.standards_page.splitter),
            ("standards_left_split", self.standards_page.left_splitter),
            ("connectors_split", self.connectors_page.splitter),
        ]:
            value = self.settings.value(key)
            if value:
                split.restoreState(value)
        self.tabs.setCurrentIndex(int(self.settings.value("tab", 0)))

    def _log(self, message, level="INFO"):
        self.log_widget.appendPlainText(
            f"{datetime.now():%H:%M:%S}  {level:<5}  {message}"
        )
        if level == "INFO":
            LOGGER.info(message)
        elif level == "WARNING":
            LOGGER.warning(message)
        else:
            LOGGER.error(message)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Keysight XKT CalKit file",
            self.settings.value("last_dir", ""),
            "XKT CalKit files (*.xkt);;All files (*)",
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        if self._loading:
            return
        self._loading = True
        self.open_button.setEnabled(False)
        self.open_act.setEnabled(False)
        self.status.showMessage(f"Loading {os.path.basename(path)}…")
        self._log(f"Loading {path}")
        self._progress = QProgressDialog("Reading calibration kit…", None, 0, 0, self)
        self._progress.setWindowTitle("Loading XKT")
        self._progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress.setMinimumDuration(0)
        self._progress.show()
        worker = _LoadWorker(path, self)
        self._worker = worker
        worker.loaded.connect(self._loaded)
        worker.failed.connect(self._failed)
        worker.finished.connect(self._finish_loading)
        worker.start()

    def _loaded(self, kit, path):
        self._kit = kit
        self._populate(kit, path)
        self.settings.setValue("last_dir", str(Path(path).parent))
        warnings = getattr(kit, "_warnings", [])
        for warning in warnings:
            self._log(warning, "WARNING")
        if warnings:
            self._progress.close()
            box = QMessageBox(self)
            box.setWindowTitle("Parse warnings")
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(
                f"Loaded with {len(warnings)} warning(s). See the activity log for details."
            )
            box.setDetailedText("\n".join(warnings))
            box.exec()

    def _failed(self, title, message, path):
        self._progress.close()
        self._log(f"{os.path.basename(path)}: {message}", "ERROR")
        self.status.showMessage(f"Load failed · {os.path.basename(path)}")
        QMessageBox.critical(self, title, message)

    def _finish_loading(self):
        if self._progress:
            self._progress.close()
        self._loading = False
        self.open_button.setEnabled(True)
        self.open_act.setEnabled(True)
        worker = self._worker
        self._worker = None
        if worker:
            worker.deleteLater()

    def _populate(self, kit: CalKitData, path: str):
        fname = os.path.basename(path)
        self.setWindowTitle(f"XKT CalKit Viewer — {fname}")
        marker = "Keysight database" if kit.db_type.lower() != "user" else "User kit"
        text = f"{kit.kit_label or kit.kit_name}  ·  {marker}"
        if kit.version:
            text += f"  ·  Rev. {kit.version}"
        self.kit_info_lbl.setText(text)
        self.kit_info_lbl.setToolTip(f"{text}\n{path}")
        self.connectors_page.load(kit)
        self.standards_page.load(kit)
        counts = {
            "connectors": len(kit.connectors),
            "standards": len(kit.standards),
            "database": sum(s.is_database_type for s in kit.standards),
            "decoded": sum(
                s.is_database_type and bool(s.s_params) for s in kit.standards
            ),
        }
        for key, n in counts.items():
            self.metrics[key].setText(str(n))
        self.status.showMessage(
            f"Loaded {fname}  ·  {counts['connectors']} connectors  ·  {counts['standards']} standards"
        )
        self._log(
            f"Loaded {fname}: {counts['standards']} standards, {counts['decoded']}/{counts['database']} database decoded."
        )

    def _show_about(self):
        QMessageBox.information(
            self,
            "About CalKit Viewer",
            "XKT CalKit Viewer\n\nLight engineering interface for the supplied CalKit parser.\n\nParser: xkt_parser.py\nGUI: xkt_viewer.py\n\nDatabase standards use decoded arrays from the parser.\nClassic standards retain the supplied approximate model.",
        )

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self.status.showMessage("Reading file · wait for completion before closing")
            event.ignore()
            return
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("window_state", self.saveState())
        self.settings.setValue("tab", self.tabs.currentIndex())
        for key, split in [
            ("standards_split", self.standards_page.splitter),
            ("standards_left_split", self.standards_page.left_splitter),
            ("connectors_split", self.connectors_page.splitter),
        ]:
            self.settings.setValue(key, split.saveState())
        super().closeEvent(event)
