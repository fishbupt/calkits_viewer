"""CalKit Viewer GUI: helpers."""

import logging

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

LOGGER = logging.getLogger(__name__)


class InfoLabel(QLabel):
    def __init__(self, text="", role="value"):
        super().__init__(str(text))
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setProperty("role", role)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)


def _freq_str(hz: float) -> str:
    if hz <= 0:
        return "--"
    for scale, unit in ((1e12, "THz"), (1e9, "GHz"), (1e6, "MHz"), (1e3, "kHz")):
        if hz >= scale:
            return f"{hz / scale:.3f} {unit}"
    return f"{hz:.0f} Hz"


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


def _card(title, subtitle=""):
    frame = QFrame()
    frame.setProperty("role", "card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    if title:
        layout.addWidget(InfoLabel(title, "title"))
    if subtitle:
        layout.addWidget(InfoLabel(subtitle, "subtle"))
    return frame, layout


def _configure_table(table, headers):
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for col in range(1, len(headers)):
        table.horizontalHeader().setSectionResizeMode(
            col, QHeaderView.ResizeMode.ResizeToContents
        )
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(38)


def _property_box(title, rows):
    box = QGroupBox(title)
    grid = QGridLayout(box)
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(9)
    grid.setColumnStretch(1, 1)
    for i, (key, value) in enumerate(rows):
        grid.addWidget(InfoLabel(key, "key"), i, 0)
        grid.addWidget(InfoLabel(value), i, 1)
    return box
