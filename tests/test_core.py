import base64
import csv
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pytest

from calkit_viewer import Standard, XKTValidationError, parse_xkt
from calkit_viewer.decoding import (
    agilent64_decode,
    agilent_corruption_list,
    base64_decode,
)
from calkit_viewer.export import write_snp, write_uncertainty_csv
from calkit_viewer.model_response import calculate_model_response


def test_demo_pipeline(demo_path, tmp_path):
    kit = parse_xkt(demo_path)
    assert len(kit.connectors) == 1 and len(kit.standards) == 5 and not kit._warnings
    s = kit.standards[-1]
    assert s.num_ports == 2 and s.is_database_type
    assert np.allclose(s.s_params["S21"], [0.96 - 0.05j, 0.95 - 0.08j, 0.94 - 0.1j])
    assert np.array_equal(s.s_params["freq"], [1e9, 2e9, 3e9])
    assert np.allclose(s.uncertainty["S11"]["Vr2"], 1e-6)
    assert np.allclose(s.uncertainty["S21"]["scalar"], [0.001, 0.002, 0.003])
    snp = tmp_path / "db.s2p"
    out = tmp_path / "u.csv"
    write_snp(snp, s)
    write_uncertainty_csv(out, s)
    assert np.allclose(
        np.fromstring(snp.read_text().splitlines()[2], sep=" "),
        [1e9, 0.025, 0.01, 0.96, -0.05, 0.95, -0.05, 0.03, 0.01],
    )
    with out.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 6 and rows[-1]["scalar"] == "0.003"


def test_zip_utf16_namespace(demo_path, tmp_path):
    path = tmp_path / "kit.xkt"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("notes.xml", "<notes/>")
        z.writestr(
            "kit.xml", demo_path.read_text().replace("utf-8", "utf-16").encode("utf-16")
        )
    assert len(parse_xkt(path).standards) == 5


@pytest.mark.parametrize(
    "text", ["", "abc", "<broken>", "<xeokit/>", "<!DOCTYPE CalKit><CalKit/>"]
)
def test_invalid_file(text, tmp_path):
    path = tmp_path / "bad.xkt"
    path.write_text(text)
    with pytest.raises((XKTValidationError, ET.ParseError)):
        parse_xkt(path)


def test_nonexistent(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_xkt(tmp_path / "none.xkt")


def test_invalid_frequency_warns(demo_path, tmp_path):
    root = ET.fromstring(demo_path.read_bytes())
    for e in root.iter():
        e.tag = e.tag.split("}")[-1]
    root.find(
        "FrequencyLists/Stimulus/Segments/Arbitrary/Base64Data"
    ).text = base64.b64encode(struct.pack("<d", -1)).decode()
    path = tmp_path / "bad.xkt"
    path.write_bytes(ET.tostring(root))
    kit = parse_xkt(path)
    assert kit.standards[-1].s_params is None and kit._warnings


def test_offset_fields(demo_path):
    s = parse_xkt(demo_path).standards[0]
    assert (
        s.offset_delay_s == 30e-12
        and s.offset_loss_ohm_per_s == 2.2e9
        and s.c0 == 50e-15
    )


@pytest.mark.parametrize("kind,target", [("Open", 1), ("Short", -1), ("Load", 0)])
def test_classic_ideal(kind, target):
    s = Standard(std_type=kind, max_freq_hz=26.5e9)
    assert np.allclose(calculate_model_response(s)["S11"], target)


def test_preserved_open_equation():
    s = Standard(
        std_type="Open", max_freq_hz=26.5e9, c0=50e-15, c1=1e-27, offset_delay_s=30e-12
    )
    data = calculate_model_response(s)
    f = data["freq"]
    w = 2 * np.pi * f
    z = 1 / (1j * w * (s.c0 + s.c1 * f) + 1e-30)
    assert np.allclose(
        data["S11"], (z - 50) / (z + 50 + 1e-30) * np.exp(-2j * w * s.offset_delay_s)
    )


def test_thru_and_classic_export(tmp_path):
    s = Standard(
        std_type="Thru", num_ports=2, max_freq_hz=26.5e9, offset_delay_s=30e-12
    )
    d = calculate_model_response(s)
    assert np.allclose(d["S21"], np.exp(-2j * np.pi * d["freq"] * s.offset_delay_s))
    path = tmp_path / "thru.s2p"
    write_snp(path, s)
    assert len(path.read_text().splitlines()) == 1002


def test_locked_and_partial_export(demo_path, tmp_path):
    with pytest.raises(ValueError):
        write_snp(tmp_path / "s.s1p", Standard(is_database_type=True, std_type="Open"))
    s = parse_xkt(demo_path).standards[-1]
    del s.s_params["S12"]
    with pytest.raises(ValueError):
        write_snp(tmp_path / "s.s2p", s)


def test_decode_cycles():
    vals = np.arange(80, dtype=float) / 17
    raw = vals.astype("<f8").tobytes()
    xor = bytes(b ^ agilent_corruption_list[i % 33] for i, b in enumerate(raw))
    enc = b"".join(xor[i : i + 8][::-1] for i in range(0, len(xor), 8))
    assert np.array_equal(
        agilent64_decode(base64.b64encode(enc)), vals[::2] + 1j * vals[1::2]
    )
    assert np.array_equal(base64_decode(base64.b64encode(raw), "float"), vals)


@pytest.mark.parametrize("func", [base64_decode, agilent64_decode])
@pytest.mark.parametrize("raw", [b"a", b"12345678"])
def test_corrupt_complex(func, raw):
    with pytest.raises(ValueError):
        func(base64.b64encode(raw))


def test_core_no_gui():
    cmd = 'import calkit_viewer; import calkit_viewer.export; import sys; assert not any(k.startswith("PyQt") for k in sys.modules)'
    result = subprocess.run([sys.executable, "-c", cmd], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
