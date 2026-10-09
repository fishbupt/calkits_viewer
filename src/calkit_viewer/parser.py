"""Keysight XML/ZIP reader based on the user's FrequencyLists/DBA schema."""

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np

from .decoding import agilent64_decode, base64_decode
from .models import CalKitData, Connector, Standard

MAX_BYTES = 64 * 1024 * 1024


class XKTValidationError(Exception):
    """XML exists but is not a supported calibration-kit structure."""


def decrypt_freq_data(raw_bytes: str | bytes):
    return base64_decode(raw_bytes, "float")


def decrypt_standard_data(raw_bytes: str | bytes, use_agilent_base64: bool = False):
    return (
        agilent64_decode(raw_bytes)
        if use_agilent_base64
        else base64_decode(raw_bytes, "complex")
    )


def decrypt_uncertainty_data(raw_bytes: str | bytes):
    return base64_decode(raw_bytes, "float")


def _text(element, tag, default=""):
    if element is None:
        return default
    node = element.find(tag)
    return node.text.strip() if node is not None and node.text else default


def _float(element, tag, default=0.0):
    text = _text(element, tag)
    if not text:
        return default
    value = float(text)
    if not np.isfinite(value):
        raise ValueError(f"{tag} must be finite")
    return value


def _bool(element, tag, default=False):
    text = _text(element, tag).lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    return default


def _parse_connector(elem):
    c = Connector()
    c.raw_element = elem
    c.name = elem.get("name", "") or _text(elem, "Name") or _text(elem, "Family")
    c.gender = _text(elem, "Gender", "Unknown")
    c.label = (
        elem.get("label", "")
        or _text(elem, "Label")
        or (f"{c.name} {c.gender}".strip() if c.gender != "Unknown" else c.name)
    )
    c.impedance = _float(elem, "Impedance") or _float(elem, "SystemZ0", 50.0)
    c.min_freq_hz = _float(elem, "MinimumFrequencyHz")
    c.max_freq_hz = _float(elem, "MaximumFrequencyHz") or _float(elem, "MaxFrequencyHz")
    return c


def _infer_std_type_from_label(label):
    label = label.upper()
    for token, kind in [
        ("SHORT", "Short"),
        ("OPEN", "Open"),
        ("LOAD", "Load"),
        ("LOWBAND", "Load"),
        ("THRU", "Thru"),
        ("LINE", "Thru"),
    ]:
        if token in label:
            return kind
    return "Database"


def _parse_standard(elem):
    s = Standard()
    s.raw_element = elem
    s.label = _text(elem, "Label")
    s.description = _text(elem, "Description")
    s.std_number = _text(elem, "StandardNumber")
    if elem.tag == "DataBasedStandard":
        s.std_type = _infer_std_type_from_label(s.label)
        s.is_database_type = True
    elif elem.tag == "ThruStandard":
        s.std_type = "Thru"
        s.num_ports = 2
    else:
        s.std_type = _text(elem, "StdType") or elem.get("type", "Unknown")
    ports = elem.findall("PortConnectorIDs")
    if ports:
        s.connector_name = (ports[0].text or "").strip()
        s.connector2_name = (ports[1].text or "").strip() if len(ports) > 1 else ""
    else:
        s.connector_name = _text(elem, "ConnectorName") or _text(elem, "Connector1Name")
        s.connector2_name = _text(elem, "Connector2Name")
    s.gender = _text(elem, "Gender")
    s.gender2 = _text(elem, "Gender2")
    s.min_freq_hz = _float(elem, "MinimumFrequencyHz")
    s.max_freq_hz = _float(elem, "MaximumFrequencyHz")
    offset = elem.find("Offset")
    if offset is None:
        offset = elem  # Do not use Element truthiness.
    s.offset_delay_s = _float(offset, "OffsetDelay")
    s.offset_loss_ohm_per_s = _float(offset, "OffsetLoss")
    s.offset_z0 = _float(offset, "OffsetZ0", 50.0)
    for name in ("C0", "C1", "C2", "C3", "L0", "L1", "L2", "L3"):
        if elem.find(name) is not None:
            setattr(s, name.lower(), _float(elem, name))
    if elem.find("TerminalImpedance") is not None:
        s.terminal_impedance = _float(elem, "TerminalImpedance", 50.0)
    if elem.find("Symmetric") is not None:
        s.is_symmetric = _bool(elem, "Symmetric")
    for dba in elem.findall("DataBasedArrays"):
        s.is_database_type = True
        rx = _text(dba, "ReceivePort", "1")
        tx = _text(dba, "SourcePort", "1")
        if (
            not rx.isdigit()
            or not tx.isdigit()
            or not 1 <= int(rx) <= 9
            or not 1 <= int(tx) <= 9
        ):
            raise ValueError("Invalid port index")
        key = f"S{rx}{tx}"
        if key in s.raw_s_data:
            raise ValueError(f"Duplicate data array {key}")
        raw = dba.findtext(".//Data/Base64Data")
        agi = dba.findtext(".//Data/AgilentData")
        s.raw_s_data[key] = {
            "freq_list_name": dba.findtext(".//Frequencies/Name"),
            "raw_data": raw,
            "agi64_raw_data": agi,
        }
        s.num_ports = max(s.num_ports, int(rx), int(tx))
    if not s.raw_s_data:
        raw = elem.findtext("Data") or elem.findtext("DatabaseData/EncryptedData")
        if raw and raw.strip():
            s.is_database_type = True
            s.raw_s_data["S11"] = {"freq_list_name": None, "raw_data": raw}
    if s.std_type.lower() in ("thru", "line", "attenuator"):
        s.num_ports = max(s.num_ports, 2)
    for acc in elem.findall("AccuracyArrays"):
        rx = _text(acc, "ReceivePort", "1")
        tx = _text(acc, "SourcePort", "1")
        key = f"S{rx}{tx}"
        if key in s.uncertainty:
            raise ValueError(f"Duplicate accuracy array {key}")
        entry = {
            "freq_list_name": acc.findtext(".//AccuracyData/Frequencies/Name"),
            "type": None,
        }
        for field in ("Vr2", "Vri", "Vi2", "scalar"):
            entry[field] = None
            entry[field + "_raw"] = None
        cov = acc.find(".//CovarianceElement")
        scalar = acc.find(".//ScalarElement")
        if cov is not None:
            entry["type"] = "Covariance"
            for field in ("Vr2", "Vri", "Vi2"):
                entry[field + "_raw"] = cov.findtext(field + "/Base64Data")
        elif scalar is not None:
            entry["type"] = "Scalar"
            entry["scalar_raw"] = scalar.findtext("Base64Data")
        s.uncertainty[key] = entry
    return s


_CALKIT_TAGS = {"CalKit", "Calkit", "CALKIT", "CalKitSave", "CalKitData"}


def _xml_root(data):
    normalized = data.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in normalized or b"<!ENTITY" in normalized:
        raise XKTValidationError("DTD/entity declarations are unsupported")
    root = ET.fromstring(data)
    for elem in root.iter():
        elem.tag = elem.tag.split("}")[-1]
        elem.attrib = {k.split("}")[-1]: v for k, v in elem.attrib.items()}
    return root


def _validate_xkt_structure(root, filepath):
    if any(word in root.tag.lower() for word in ("scene", "model", "geometry", "mesh")):
        raise XKTValidationError("This XML is not a CalKit file")
    if {c.tag.lower() for c in root} & {
        "geometries",
        "meshes",
        "entities",
        "positions",
        "indices",
    }:
        raise XKTValidationError("Unrelated XKT geometry content")
    kit = (
        root
        if root.tag in _CALKIT_TAGS
        else next((e for e in root.iter() if e.tag in _CALKIT_TAGS), None)
    )
    if kit is None:
        if any(
            root.find(".//" + t) is not None
            for t in (
                "Connector",
                "Coaxial",
                "Standard",
                "DataBasedStandard",
                "ThruStandard",
                "ConnectorList",
                "StandardList",
                "CalKitLabel",
            )
        ):
            kit = root
        else:
            raise XKTValidationError(f"No CalKit structure in {Path(filepath).name}")
    warnings = []
    if not any(kit.find(".//" + t) is not None for t in ("Connector", "Coaxial")):
        warnings.append("No connector elements found")
    if not any(
        kit.find(".//" + t) is not None
        for t in ("Standard", "DataBasedStandard", "ThruStandard")
    ):
        warnings.append("No standard elements found")
    return kit, warnings


def _read_root(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise XKTValidationError(f"Path is not a file: {path}")
    if not 0 < path.stat().st_size <= MAX_BYTES:
        raise XKTValidationError("Empty file or file larger than 64 MiB")
    if not zipfile.is_zipfile(path):
        return _xml_root(path.read_bytes())
    with zipfile.ZipFile(path) as z:
        entries = [
            i
            for i in z.infolist()
            if i.filename.lower().endswith(".xml") and not i.is_dir()
        ]
        if not entries:
            raise XKTValidationError("ZIP contains no XML entry")
        if sum(i.file_size for i in entries) > MAX_BYTES:
            raise XKTValidationError("ZIP XML larger than 64 MiB")
        candidates = []
        for item in entries:
            try:
                root = _xml_root(z.read(item))
                _validate_xkt_structure(root, path)
                candidates.append(root)
            except (ET.ParseError, XKTValidationError):
                continue
        if len(candidates) != 1:
            raise XKTValidationError("ZIP must contain one unambiguous CalKit XML")
        return candidates[0]


def _axis(values):
    arr = np.asarray(values, dtype=float)
    if (
        arr.ndim != 1
        or not len(arr)
        or not np.isfinite(arr).all()
        or (arr < 0).any()
        or (np.diff(arr) <= 0).any()
    ):
        raise ValueError(
            "Frequency axis must be finite, nonnegative and strictly increasing"
        )
    return arr


def _data_array(values, freq, complex_values=False):
    arr = np.asarray(values, dtype=complex if complex_values else float)
    if arr.shape != freq.shape or not np.isfinite(arr).all():
        raise ValueError("Data length or values do not match frequency axis")
    return arr


def _resolve_axis(kit, name):
    if name:
        return kit.frequency_lists.get(name.strip())
    axes = [f for f in kit.frequency_lists.values() if f is not None]
    return axes[0] if len(axes) == 1 else None


def parse_xkt(filepath: str | Path) -> CalKitData:
    path = Path(filepath)
    root = _read_root(path)
    element, warnings = _validate_xkt_structure(root, path)
    kit = CalKitData(raw_root=root, _warnings=warnings)
    kit.kit_name = (
        element.get("name", "")
        or _text(element, "CalKitLabel")
        or _text(element, "Name")
        or _text(element, "KitName")
        or path.stem
    )
    kit.kit_label = (
        _text(element, "CalKitLabel") or _text(element, "Label") or kit.kit_name
    )
    kit.description = _text(element, "CalKitDescription") or _text(
        element, "Description"
    )
    kit.author = _text(element, "Author") or _text(element, "Company")
    kit.version = (
        _text(element, "CalKitVersion")
        or _text(element, "Revision")
        or _text(element, "Version")
    )
    kit.db_type = _text(element, "DatabaseType") or _text(
        element, "CalKitType", "Keysight"
    )
    for fl in element.findall("FrequencyLists"):
        name = _text(fl, "Name")
        if not name:
            continue
        if name in kit.frequency_lists:
            kit._warnings.append(f"Duplicate frequency list {name}")
            continue
        kit.frequency_lists[name] = None
        raw = fl.findtext(".//Stimulus/Segments/Arbitrary/Base64Data")
        try:
            if not raw:
                raise ValueError("Missing frequency Base64Data")
            kit.frequency_lists[name] = _axis(decrypt_freq_data(raw))
        except Exception as exc:
            kit._warnings.append(f"FrequencyList {name}: {exc}")
    con_parent = next(
        (
            element.find(t)
            for t in ("ConnectorList", "Connectors")
            if element.find(t) is not None
        ),
        element,
    )
    for elem in con_parent:
        if elem.tag not in ("Connector", "Coaxial"):
            continue
        try:
            kit.connectors.append(_parse_connector(elem))
        except Exception as exc:
            kit._warnings.append(f"Skipped malformed connector: {exc}")
    std_parent = next(
        (
            element.find(t)
            for t in ("StandardList", "Standards")
            if element.find(t) is not None
        ),
        element,
    )
    for elem in std_parent:
        if elem.tag not in ("Standard", "DataBasedStandard", "ThruStandard"):
            continue
        try:
            std = _parse_standard(elem)
        except Exception as exc:
            kit._warnings.append(f"Skipped standard {_text(elem, 'Label')}: {exc}")
            continue
        arrays = {}
        common_axis = None
        for key, entry in std.raw_s_data.items():
            try:
                freq = _resolve_axis(kit, entry.get("freq_list_name"))
                if freq is None:
                    raise ValueError("Frequency list unavailable")
                raw = entry.get("raw_data")
                agi = entry.get("agi64_raw_data")
                if raw and agi:
                    raise ValueError("Both Base64Data and AgilentData supplied")
                if not raw and not agi:
                    raise ValueError("S data missing")
                values = _data_array(
                    decrypt_standard_data(agi if agi else raw, bool(agi)), freq, True
                )
                if common_axis is not None and not np.array_equal(common_axis, freq):
                    raise ValueError("S-parameter frequency axes differ")
                common_axis = freq
                arrays[key] = values
            except Exception as exc:
                kit._warnings.append(f"{std.label} {key}: {exc}")
        if arrays and len(arrays) == len(std.raw_s_data):
            std.s_params = {"freq": common_axis, **arrays}
        for key, entry in std.uncertainty.items():
            freq = _resolve_axis(kit, entry.get("freq_list_name"))
            if freq is not None:
                entry["freq"] = freq
            for field in ("Vr2", "Vri", "Vi2", "scalar"):
                raw = entry.get(field + "_raw")
                if raw is None:
                    continue
                try:
                    if freq is None:
                        raise ValueError("Uncertainty frequency list unavailable")
                    entry[field] = _data_array(decrypt_uncertainty_data(raw), freq)
                except Exception as exc:
                    kit._warnings.append(f"{std.label} {key} {field}: {exc}")
        kit.standards.append(std)
    return kit
