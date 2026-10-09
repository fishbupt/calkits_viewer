"""Classic approximations preserved from the user's GUI; not a new loss model."""

import numpy as np

from .models import Standard


def calculate_model_response(standard: Standard) -> dict[str, np.ndarray]:
    f_max = standard.max_freq_hz if standard.max_freq_hz > 0 else 20e9
    freq = np.linspace(0, f_max, 1000)
    freq[0] = 1e6  # Preserve the supplied non-DC grid.
    omega = 2 * np.pi * freq
    Z0 = 50.0
    stype = standard.std_type.lower()
    if stype == "open":
        C = (
            (standard.c0 or 0)
            + (standard.c1 or 0) * freq
            + (standard.c2 or 0) * freq**2
            + (standard.c3 or 0) * freq**3
        )
        Z = 1 / (1j * omega * C + 1e-30)
        S11 = (Z - Z0) / (Z + Z0 + 1e-30)
        S11 *= np.exp(-2j * omega * standard.offset_delay_s)
        return {"freq": freq, "S11": S11}
    if stype == "short":
        L = (
            (standard.l0 or 0)
            + (standard.l1 or 0) * freq
            + (standard.l2 or 0) * freq**2
            + (standard.l3 or 0) * freq**3
        )
        Z = 1j * omega * L
        S11 = (Z - Z0) / (Z + Z0 + 1e-30)
        S11 *= np.exp(-2j * omega * standard.offset_delay_s)
        return {"freq": freq, "S11": S11}
    if stype in ("load", "broadband load"):
        Rt = standard.terminal_impedance or Z0
        Z = np.full_like(freq, Rt, dtype=complex)
        return {"freq": freq, "S11": (Z - Z0) / (Z + Z0 + 1e-30)}
    if stype in ("thru", "line"):
        S21 = np.exp(-1j * omega * standard.offset_delay_s)
        S11 = np.zeros_like(freq, dtype=complex)
        return {
            "freq": freq,
            "S11": S11,
            "S21": S21.copy(),
            "S12": S21.copy(),
            "S22": S11.copy(),
        }
    raise ValueError(f"No model for {standard.std_type}")
