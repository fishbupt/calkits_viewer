"""CalKit Viewer GUI: pages."""

import logging
import re
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6.QtCore import (
    QSettings,
    QSignalBlocker,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from calkit_viewer.export import write_snp, write_uncertainty_csv
from calkit_viewer.parser import (
    CalKitData,
    Connector,
    Standard,
)

from .helpers import (
    InfoLabel,
    _card,
    _clear_layout,
    _configure_table,
    _freq_str,
    _property_box,
)
from .plot import SParamPlot
from .theme import TYPE_COLORS

LOGGER = logging.getLogger(__name__)


class ConnectorsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self._connectors = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 14, 0, 0)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        left, lv = _card(
            "Connectors", "Select a connector to inspect its electrical definition."
        )
        self.table = QTableWidget()
        _configure_table(
            self.table, ["Name", "Gender", "Z0 (Ω)", "Min Freq", "Max Freq"]
        )
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        lv.addWidget(self.table, 1)
        right, rv = _card("Connector details")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.detail_widget = QWidget()
        self.detail_widget.setObjectName("cardContent")
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(12)
        scroll.setWidget(self.detail_widget)
        rv.addWidget(scroll, 1)
        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setSizes([760, 430])
        layout.addWidget(self.splitter, 1)
        self._empty()

    def _empty(self):
        _clear_layout(self.detail_layout)
        self.detail_layout.addWidget(
            InfoLabel("Select a connector to view its properties.", "subtle")
        )
        self.detail_layout.addStretch()

    def load(self, kit: CalKitData):
        blocker = QSignalBlocker(self.table)
        self.table.setRowCount(0)
        self._connectors = kit.connectors
        for c in self._connectors:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, val in enumerate(
                [
                    c.label or c.name,
                    c.gender,
                    f"{c.impedance:.1f}",
                    _freq_str(c.min_freq_hz),
                    _freq_str(c.max_freq_hz),
                ]
            ):
                item = QTableWidgetItem(val)
                item.setToolTip(val)
                self.table.setItem(row, col, item)
        del blocker
        self._empty()
        if self._connectors:
            self.table.selectRow(0)

    def _on_selection_changed(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._connectors):
            self._show_detail(self._connectors[row])

    def _show_detail(self, c: Connector):
        _clear_layout(self.detail_layout)
        self.detail_layout.addWidget(InfoLabel(c.label or c.name, "title"))
        self.detail_layout.addWidget(
            _property_box(
                "Connector properties",
                [
                    ("Name", c.name),
                    ("Label", c.label),
                    ("Gender", c.gender),
                    ("Impedance", f"{c.impedance:.2f} Ω"),
                    ("Min frequency", _freq_str(c.min_freq_hz)),
                    ("Max frequency", _freq_str(c.max_freq_hz)),
                ],
            )
        )
        self.detail_layout.addStretch()


class StandardsPage(QWidget):
    notice = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self._kit: Optional[CalKitData] = None
        self._standards = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 14, 0, 0)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        left = QSplitter(Qt.Orientation.Vertical)
        left.setChildrenCollapsible(False)
        list_card, lv = _card(
            "Standards", "Right-click a standard to export available data."
        )
        self.table = QTableWidget()
        _configure_table(
            self.table, ["Label", "Type", "Connector", "Gender", "Max Freq"]
        )
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        lv.addWidget(self.table, 1)
        properties_card, pv = _card("Properties")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.prop_widget = QWidget()
        self.prop_widget.setObjectName("cardContent")
        self.prop_layout = QVBoxLayout(self.prop_widget)
        self.prop_layout.setContentsMargins(0, 0, 0, 0)
        self.prop_layout.setSpacing(12)
        scroll.setWidget(self.prop_widget)
        pv.addWidget(scroll, 1)
        left.addWidget(list_card)
        left.addWidget(properties_card)
        left.setSizes([340, 430])
        self.left_splitter = left
        right, rv = _card("S-parameter response")
        head = QHBoxLayout()
        self.plot_title = InfoLabel("No standard selected")
        self.plot_badge = InfoLabel("Ready", "badge")
        head.addWidget(self.plot_title, 1)
        head.addWidget(self.plot_badge)
        rv.addLayout(head)
        self.plot_widget = SParamPlot()
        rv.addWidget(self.plot_widget, 1)
        self.plot_summary = InfoLabel(
            "Select a standard to inspect magnitude and phase.", "subtle"
        )
        rv.addWidget(self.plot_summary)
        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setSizes([460, 940])
        layout.addWidget(self.splitter, 1)
        self._clear_properties()

    def _clear_properties(self):
        _clear_layout(self.prop_layout)
        self.prop_layout.addWidget(
            InfoLabel("Select a standard to view its definition.", "subtle")
        )
        self.prop_layout.addStretch()

    def load(self, kit: CalKitData):
        self._kit = kit
        blocker = QSignalBlocker(self.table)
        self.table.setRowCount(0)
        self._standards = kit.standards
        self._clear_properties()
        self.plot_widget.clear_plot()
        self.plot_title.setText("No standard selected")
        self.plot_badge.setText("Ready")
        self.plot_summary.setText("Select a standard to inspect magnitude and phase.")
        for std in self._standards:
            row = self.table.rowCount()
            self.table.insertRow(row)
            vals = [
                std.label,
                std.std_type,
                std.connector_name or "--",
                std.gender or "--",
                _freq_str(std.max_freq_hz),
            ]
            for col, value in enumerate(vals):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if col == 1:
                    item.setForeground(
                        QBrush(QColor(TYPE_COLORS.get(std.std_type.lower(), "#53647a")))
                    )
                if col == 0 and std.is_database_type:
                    item.setToolTip(
                        "Database standard — decoded arrays used when available."
                    )
                self.table.setItem(row, col, item)
        del blocker
        if self._standards:
            self.table.selectRow(0)

    def _on_selection_changed(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._standards):
            std = self._standards[row]
            self._show_properties(std)
            self._update_plot(std)

    def _show_properties(self, s: Standard):
        _clear_layout(self.prop_layout)
        self.prop_layout.addWidget(InfoLabel(s.label, "title"))
        rows = [("Type", s.std_type), ("Connector", s.connector_name or "--")]
        if s.connector2_name:
            rows.append(("Connector 2", s.connector2_name))
        rows.extend(
            [
                ("Gender", s.gender or "--"),
                ("Offset delay", f"{s.offset_delay_s * 1e12:.4f} ps"),
                ("Offset loss", f"{s.offset_loss_ohm_per_s:.4e} Ω/s"),
                ("Offset Z0", f"{s.offset_z0:.2f} Ω"),
                ("Min frequency", _freq_str(s.min_freq_hz)),
                ("Max frequency", _freq_str(s.max_freq_hz)),
            ]
        )
        self.prop_layout.addWidget(_property_box("Standard properties", rows))
        coefs = []
        for name, unit in [
            ("c0", "F"),
            ("c1", "F/Hz"),
            ("c2", "F/Hz²"),
            ("c3", "F/Hz³"),
            ("l0", "H"),
            ("l1", "H/Hz"),
            ("l2", "H/Hz²"),
            ("l3", "H/Hz³"),
        ]:
            value = getattr(s, name)
            if value is not None:
                coefs.append((f"{name.upper()} ({unit})", f"{value:.6e}"))
        if coefs:
            self.prop_layout.addWidget(_property_box("Polynomial coefficients", coefs))
        if s.terminal_impedance is not None:
            self.prop_layout.addWidget(
                _property_box(
                    "Load properties",
                    [("Terminal impedance", f"{s.terminal_impedance:.4f} Ω")],
                )
            )
        if s.is_database_type:
            raw_count = sum(
                len(e.get("raw_data") or e.get("agi64_raw_data") or b"")
                for e in s.raw_s_data.values()
            )
            if s.s_params:
                status = f"Decoded · {len(s.s_params) - 1} S-parameter(s)"
            elif raw_count:
                status = "Data present · decoding unavailable or failed; see parser warnings."
            else:
                status = "No database data found."
            self.prop_layout.addWidget(
                _property_box(
                    "Database data",
                    [
                        ("Status", status),
                        ("Parameters", ", ".join(s.raw_s_data) or "--"),
                        ("Ports", str(s.num_ports)),
                    ],
                )
            )
        self.prop_layout.addStretch()

    def _update_plot(self, std: Standard):
        self.plot_title.setText(std.label)
        try:
            if std.is_database_type:
                if std.s_params:
                    self.plot_badge.setText("Database")
                    self.plot_widget.plot_s_params(std.s_params, std)
                    f = np.asarray(std.s_params.get("freq", []))
                    self.plot_summary.setText(
                        f"{len(f):,} points  ·  {_freq_str(f[0])} – {_freq_str(f[-1])}  ·  {std.num_ports} port(s)"
                        if len(f)
                        else "No frequency data"
                    )
                else:
                    self.plot_badge.setText("Unavailable")
                    self.plot_widget.show_placeholder(
                        "Database data unavailable",
                        "Check the parser warnings for this standard.",
                    )
                    self.plot_summary.setText(
                        "No decoded arrays available for plotting or S-parameter export."
                    )
            else:
                self.plot_badge.setText("Polynomial model")
                self.plot_widget.plot_model_response(std)
                self.plot_summary.setText(
                    f"{std.std_type} model  ·  1,000 points  ·  classic approximation from supplied source"
                )
        except Exception as exc:
            LOGGER.exception("Plot failed")
            self.plot_widget.show_placeholder("Unable to plot data", str(exc))
            self.plot_summary.setText("Plot error · see activity log")
            self.notice.emit(f"Plot failed: {exc}", "ERROR")

    def _on_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item is None:
            return
        self.table.selectRow(item.row())
        std = self._standards[item.row()]
        menu = QMenu(self)
        act = menu.addAction(f"Export S-parameters → .s{std.num_ports}p")
        act.setEnabled(
            bool(std.s_params)
            or (
                not std.is_database_type
                and std.std_type.lower()
                in ("open", "short", "load", "broadband load", "thru", "line")
            )
        )
        act.triggered.connect(lambda: self._export_snp(std))
        has_unc = any(
            any(e.get(k) is not None for k in ("Vr2", "Vi2", "scalar"))
            for e in std.uncertainty.values()
        )
        act = menu.addAction("Export uncertainty → .csv")
        act.setEnabled(has_unc)
        act.triggered.connect(lambda: self._export_uncertainty(std))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _export_snp(self, std: Standard):
        self._export(std, False)

    def _export_uncertainty(self, std: Standard):
        self._export(std, True)

    def _export(self, std, uncertainty):
        ext = ".csv" if uncertainty else f".s{std.num_ports}p"
        name = (
            re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", std.label).strip(". ") or "standard"
        )
        settings = QSettings("Keysight Tools", "XKT CalKit Viewer")
        default = str(
            Path(settings.value("export_dir", str(Path.home())))
            / (name + ("_uncertainty" if uncertainty else "") + ext)
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save uncertainty CSV" if uncertainty else "Save Touchstone file",
            default,
            f"Export (*{ext});;All files (*)",
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ext
        try:
            if uncertainty:
                write_uncertainty_csv(path, std)
            else:
                write_snp(path, std)
            settings.setValue("export_dir", str(Path(path).parent))
            self.notice.emit(f"Exported {path}", "INFO")
            QMessageBox.information(self, "Export complete", f"Data saved to:\n{path}")
        except Exception as exc:
            LOGGER.exception("Export failed")
            self.notice.emit(f"Export failed: {exc}", "ERROR")
            QMessageBox.critical(self, "Export failed", str(exc))
