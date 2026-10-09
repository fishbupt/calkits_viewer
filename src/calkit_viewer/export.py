"""Touchstone and uncertainty CSV exports using the user's Standard objects."""

import csv
from pathlib import Path

import numpy as np

from .model_response import calculate_model_response
from .models import Standard
from .parser import _axis


def write_snp(path: str | Path, standard: Standard, z0: float = 50.0):
    if standard.is_database_type and standard.s_params is None:
        raise ValueError("Database S data is unavailable")
    data = (
        standard.s_params
        if standard.s_params is not None
        else calculate_model_response(standard)
    )
    freq = _axis(data["freq"])
    n = standard.num_ports
    order = (
        ["S11", "S21", "S12", "S22"]
        if n == 2
        else [f"S{i}{j}" for i in range(1, n + 1) for j in range(1, n + 1)]
    )
    if any(key not in data for key in order):
        raise ValueError("Incomplete S matrix cannot be exported")
    values = [np.asarray(data[key], dtype=complex) for key in order]
    if any(v.shape != freq.shape or not np.isfinite(v).all() for v in values):
        raise ValueError("Invalid S-parameter arrays")
    if not np.isfinite(z0) or z0 <= 0:
        raise ValueError("Reference impedance must be positive")
    path = Path(path)
    if path.suffix.lower() != f".s{n}p":
        raise ValueError(f"Expected .s{n}p extension")
    with path.open("w", encoding="ascii", newline="\n") as out:
        out.write(
            f"! CalKit Viewer; reference impedance explicitly specified\n# Hz S RI R {z0:.16g}\n"
        )
        for i, hz in enumerate(freq):
            row = [hz] + [
                value for arr in values for value in (arr[i].real, arr[i].imag)
            ]
            out.write(" ".join(f"{v:.16g}" for v in row) + "\n")


def write_uncertainty_csv(path: str | Path, standard: Standard):
    rows = []
    for key, entry in standard.uncertainty.items():
        parts = [
            field
            for field in ("Vr2", "Vri", "Vi2", "scalar")
            if entry.get(field) is not None
        ]
        if not parts:
            continue
        freq = entry.get("freq")
        if freq is None:
            raise ValueError(f"{key}: uncertainty frequency axis unavailable")
        freq = _axis(freq)
        if any(
            np.asarray(entry[field]).shape != freq.shape
            or not np.isfinite(entry[field]).all()
            for field in parts
        ):
            raise ValueError(f"{key}: invalid uncertainty arrays")
        for i, hz in enumerate(freq):
            rows.append(
                [key, entry.get("type", ""), hz]
                + [
                    entry[field][i] if field in parts else ""
                    for field in ("Vr2", "Vri", "Vi2", "scalar")
                ]
            )
    if not rows:
        raise ValueError("No decoded uncertainty data to export")
    with Path(path).open("w", encoding="utf-8-sig", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(
            ["S_parameter", "type", "frequency_Hz", "Vr2", "Vri", "Vi2", "scalar"]
        )
        writer.writerows(rows)
