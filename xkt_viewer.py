"""Compatibility GUI entry point: uv run python xkt_viewer.py [file.xkt]."""

from calkit_viewer.gui.app import main as main
from calkit_viewer.gui.helpers import InfoLabel as InfoLabel
from calkit_viewer.gui.pages import (
    ConnectorsPage as ConnectorsPage,
)
from calkit_viewer.gui.pages import (
    StandardsPage as StandardsPage,
)
from calkit_viewer.gui.plot import SParamPlot as SParamPlot
from calkit_viewer.gui.window import XKTViewer as XKTViewer

if __name__ == "__main__":
    raise SystemExit(main())
