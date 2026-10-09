"""CalKit Viewer GUI: plot."""

import logging

import numpy as np
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from calkit_viewer.model_response import calculate_model_response
from calkit_viewer.parser import (
    Standard,
)

from .theme import S_COLORS

LOGGER = logging.getLogger(__name__)


class SParamPlot(QWidget):
    """White plots; fixed S-parameter colors, dashed phase on a second Y axis."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.fig = Figure(
            figsize=(9, 6), dpi=100, layout="constrained", facecolor="white"
        )
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(360)
        self.nav = NavigationToolbar(self.canvas, self)
        self.nav.setObjectName("plotToolbar")
        layout.addWidget(self.nav)
        layout.addWidget(self.canvas, 1)
        self.clear_plot()

    def plot_s_params(self, s_params: dict, standard: Standard):
        self.fig.clear()
        freq = np.asarray(s_params.get("freq", []), dtype=float)
        candidates = ["S11"] if standard.num_ports < 2 else ["S11", "S21", "S12", "S22"]
        valid = [k for k in candidates if k in s_params]
        if not len(freq) or not valid:
            self.show_placeholder(
                "No S-parameter data", "This standard contains no plottable data."
            )
            return
        rows, cols = (2, 2) if len(valid) > 2 else (1, len(valid))
        axes = self.fig.subplots(rows, cols, squeeze=False).ravel()
        for ax, key in zip(axes, valid):
            z = np.asarray(s_params[key], dtype=complex)
            if z.shape != freq.shape:
                self.show_placeholder(
                    "Data length mismatch",
                    f"{key}: S-parameter and frequency arrays differ.",
                )
                return
            color = S_COLORS[key]
            secondary = ax.twinx()
            ax.set_facecolor("white")
            ax.plot(
                freq / 1e9,
                20 * np.log10(np.abs(z) + 1e-30),
                color=color,
                lw=1.7,
                label="Magnitude (dB)",
            )
            secondary.plot(
                freq / 1e9,
                np.angle(z, deg=True),
                color="#9b7d47",
                lw=1.1,
                ls="--",
                label="Phase (deg)",
            )
            ax.set_title(
                key, loc="left", color=color, fontsize=11, fontweight="bold", pad=10
            )
            ax.set_xlabel("Frequency (GHz)", color="#718096", fontsize=9)
            ax.set_ylabel("Magnitude (dB)", color=color, fontsize=9)
            secondary.set_ylabel("Phase (deg)", color="#9b7d47", fontsize=9)
            ax.ticklabel_format(axis="y", style="plain", useOffset=False)
            magnitude = 20 * np.log10(np.abs(z) + 1e-30)
            if np.ptp(magnitude) < 1e-6:
                center = float(np.mean(magnitude))
                ax.set_ylim(center - 0.1, center + 0.1)
            ax.tick_params(colors="#718096", labelsize=8)
            secondary.tick_params(colors="#9b7d47", labelsize=8)
            for axis in (ax, secondary):
                for spine in axis.spines.values():
                    spine.set_color("#dce3ec")
            ax.grid(True, color="#e5eaf1", lw=0.7)
            ax.set_axisbelow(True)
            lines, labs = ax.get_legend_handles_labels()
            lines2, labs2 = secondary.get_legend_handles_labels()
            ax.legend(
                lines + lines2,
                labs + labs2,
                loc="best",
                fontsize=8,
                facecolor="white",
                edgecolor="#e5eaf1",
                labelcolor="#53647a",
                framealpha=0.9,
            )
        for ax in axes[len(valid) :]:
            ax.set_visible(False)
        self.canvas.draw_idle()

    def plot_model_response(self, standard: Standard):
        """Delegate to the preserved GUI-free classic approximation."""
        try:
            data = calculate_model_response(standard)
        except ValueError as exc:
            self.show_placeholder("Model not available", str(exc))
            return False
        self.plot_s_params(data, standard)
        return True

    def show_placeholder(self, message: str, sub: str = ""):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.axis("off")
        ax.text(
            0.5,
            0.55,
            message,
            ha="center",
            va="center",
            color="#53647a",
            fontsize=13,
            fontweight="bold",
            transform=ax.transAxes,
        )
        if sub:
            ax.text(
                0.5,
                0.43,
                sub,
                ha="center",
                va="center",
                color="#94a3b8",
                fontsize=10,
                transform=ax.transAxes,
                wrap=True,
            )
        self.canvas.draw_idle()

    def clear_plot(self):
        self.show_placeholder(
            "Select a standard", "Magnitude and phase will appear here."
        )
