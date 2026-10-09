"""Shared light engineering theme and fixed object colors."""

S_COLORS = {"S11": "#2563eb", "S21": "#168367", "S12": "#c77616", "S22": "#8059b4"}

TYPE_COLORS = {
    "open": "#168367",
    "short": "#2563eb",
    "load": "#b36c18",
    "broadband load": "#b36c18",
    "thru": "#8059b4",
    "line": "#8059b4",
    "database": "#53647a",
}

STYLE_SHEET = """
QMainWindow, QWidget { background:#eef2f7; color:#273449;
    font-family:"Microsoft YaHei", "Segoe UI"; font-size:12px; }
QWidget#central, QWidget#page { background:#eef2f7; }
QWidget#cardContent { background:white; }
QWidget#toolbarSpacer { background:transparent; }
QFrame[role="card"], QGroupBox { background:#ffffff; border:1px solid #dce3ec; border-radius:8px; }
QFrame[role="card"] > QWidget, QGroupBox > QWidget { background:transparent; }
QLabel { background:transparent; border:none; }
QLabel[role="title"] { color:#202d41; font-size:17px; font-weight:600; }
QLabel[role="key"] { color:#718096; font-size:11px; }
QLabel[role="value"] { color:#334155; }
QLabel[role="subtle"] { color:#758399; font-size:11px; }
QLabel[role="metric"] { color:#223249; font-size:22px; font-weight:600; }
QLabel[role="badge"] { background:#eaf2ff; color:#2563eb; border-radius:5px; padding:5px 10px; }
QLabel[role="encrypted"] { color:#b7791f; }
QGroupBox { margin-top:10px; padding:12px 8px 8px; font-size:12px; font-weight:600; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 6px; color:#54647a; }
QTabWidget::pane { border:0; }
QTabBar::tab { background:transparent; color:#748299; padding:11px 20px;
    border:0; border-bottom:2px solid transparent; font-weight:600; }
QTabBar::tab:selected { color:#2563eb; border-bottom:2px solid #2563eb; }
QTabBar::tab:hover:!selected { background:#e6edf6; color:#334155; }
QTableWidget { background:white; alternate-background-color:#f8fafc; gridline-color:#edf1f6;
    border:0; selection-background-color:#eaf2ff; selection-color:#1d4f9b; outline:0; }
QTableWidget::item { padding:7px 8px; border-bottom:1px solid #edf1f6; }
QTableWidget::item:selected { background:#eaf2ff; color:#1d4f9b; }
QHeaderView::section { background:#f4f7fb; color:#64748b; padding:9px 8px;
    border:0; border-bottom:1px solid #dce3ec; font-size:11px; font-weight:600; }
QTableCornerButton::section { background:#f4f7fb; border:0; }
QScrollArea { background:transparent; border:0; }
QScrollBar:vertical { background:transparent; width:9px; margin:2px; }
QScrollBar:horizontal { background:transparent; height:9px; margin:2px; }
QScrollBar::handle { background:#cbd5e1; border-radius:3px; min-height:24px; min-width:24px; }
QScrollBar::handle:hover { background:#98aac0; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
QSplitter::handle { background:transparent; }
QSplitter::handle:hover { background:#c8d7ec; }
QPushButton, QToolButton { background:white; color:#405169; border:1px solid #d6dfeb;
    border-radius:5px; padding:7px 13px; }
QPushButton:hover, QToolButton:hover { background:#f1f6ff; border-color:#a9c7f4; }
QPushButton:pressed, QToolButton:pressed { background:#e4edfc; }
QPushButton[role="primary"] { background:#2563eb; color:white; border:1px solid #2563eb; font-weight:600; }
QPushButton[role="primary"]:hover { background:#1d4ed8; }
QPushButton:disabled, QToolButton:disabled { color:#a8b1bd; background:#f3f5f8; border-color:#e4e9ef; }
QToolBar { background:white; border:0; spacing:5px; padding:5px; }
QToolBar#mainToolbar { border-bottom:1px solid #dce3ec; padding:10px 16px; }
QToolBar#plotToolbar QToolButton { padding:5px; border:0; background:transparent; }
QToolBar#plotToolbar QToolButton:hover { background:#eaf2ff; }
QStatusBar { background:white; color:#718096; border-top:1px solid #dce3ec; padding:3px; }
QMenu { background:white; border:1px solid #d6dfeb; padding:5px; }
QMenu::item { padding:8px 22px; border-radius:4px; }
QMenu::item:selected { background:#eaf2ff; color:#2563eb; }
QMenu::item:disabled { color:#a1aabb; }
QPlainTextEdit { background:white; color:#53647a; border:0; font-family:"Consolas","Courier New"; font-size:11px; }
QDockWidget { color:#53647a; }
QDockWidget::title { background:#f5f8fc; padding:7px 12px; border-top:1px solid #dce3ec; }
QMessageBox, QProgressDialog { background:#f8fafc; }
"""
