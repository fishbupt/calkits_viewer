"""The user's CalKit fields, with GUI-free typed defaults and SI units."""

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Connector:
    name: str = ""
    label: str = ""
    gender: str = ""  # Male / Female / Both / Unknown.
    impedance: float = 50.0  # System reference impedance, ohms.
    min_freq_hz: float = 0.0
    max_freq_hz: float = 0.0
    raw_element: Any = None  # Source XML element.


@dataclass
class Standard:
    label: str = ""
    description: str = ""
    std_type: str = ""  # Open / Short / Load / Thru / Database / ...
    std_number: str = ""
    connector_name: str = ""
    connector2_name: str = ""
    gender: str = ""
    gender2: str = ""
    offset_delay_s: float = 0.0  # One-way delay, seconds.
    offset_loss_ohm_per_s: float = 0.0  # Offset loss coefficient, ohms/second.
    offset_z0: float = 50.0  # Offset impedance, ohms.
    min_freq_hz: float = 0.0
    max_freq_hz: float = 0.0
    c0: float | None = None  # F.
    c1: float | None = None  # F/Hz.
    c2: float | None = None  # F/Hz².
    c3: float | None = None  # F/Hz³.
    l0: float | None = None  # H.
    l1: float | None = None  # H/Hz.
    l2: float | None = None  # H/Hz².
    l3: float | None = None  # H/Hz³.
    terminal_impedance: float | None = None  # Ohms.
    is_symmetric: bool | None = None
    is_database_type: bool = False
    num_ports: int = 1
    raw_s_data: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )  # Base64 text: raw_data/agi64_raw_data and freq_list_name.
    s_params: dict[str, np.ndarray] | None = (
        None  # freq (Hz) and complex128 S11/S21/... arrays.
    )
    uncertainty: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )  # Original Vr2/Vri/Vi2/scalar keys plus resolved freq.
    raw_element: Any = None


@dataclass
class CalKitData:
    kit_name: str = ""
    kit_label: str = ""
    description: str = ""
    author: str = ""
    version: str = ""
    db_type: str = ""
    connectors: list[Connector] = field(default_factory=list)
    standards: list[Standard] = field(default_factory=list)
    frequency_lists: dict[str, np.ndarray | None] = field(
        default_factory=dict
    )  # Hz or None if decoding failed.
    _warnings: list[str] = field(default_factory=list)
    raw_root: Any = None
