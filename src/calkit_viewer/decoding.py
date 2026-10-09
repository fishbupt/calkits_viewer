"""User-supplied Base64 and Agilent reversal/XOR algorithm, with validation."""

import base64

import numpy as np


def decode_base64(text):
    if not isinstance(text, (str, bytes)):
        raise TypeError("输入必须是 Base64 字符串或 ASCII bytes")
    compact = (b"" if isinstance(text, bytes) else "").join(text.split())
    return base64.b64decode(compact, validate=True)


def tuple_double_to_real(raw_bytes):
    if len(raw_bytes) % 8:
        raise ValueError("float64 数据长度必须是 8 的倍数")
    return np.frombuffer(raw_bytes, dtype="<f8").copy()


def tuple_double_to_complex(raw_bytes):
    if len(raw_bytes) % 16:
        raise ValueError("复数数据长度必须是 16 的倍数")
    p = tuple_double_to_real(raw_bytes).reshape(-1, 2)
    return p[:, 0] + 1j * p[:, 1]


agilent_corruption_list = [
    214,
    98,
    252,
    35,
    7,
    109,
    197,
    219,
    10,
    61,
    245,
    210,
    150,
    135,
    17,
    128,
    24,
    208,
    221,
    151,
    64,
    228,
    56,
    40,
    190,
    172,
    215,
    164,
    253,
    11,
    43,
    39,
    20,
]


def base64_decode(b64_str: str | bytes, data_type="complex"):
    """Decode Base64 *text*, then read little-endian float64 values."""
    if data_type not in ("complex", "float", "real"):
        raise ValueError("data_type 应为 complex / float / real")
    raw = decode_base64(b64_str)
    return (
        tuple_double_to_complex(raw)
        if data_type == "complex"
        else tuple_double_to_real(raw)
    )


def agilent64_decode(b64_str: str | bytes, corruption_list=agilent_corruption_list):
    """User-supplied algorithm: reverse each 8-byte unit, XOR, pair as complex."""
    mask = list(corruption_list)
    if len(mask) != 33 or any(
        not isinstance(x, (int, np.integer)) or not 0 <= x <= 255 for x in mask
    ):
        raise ValueError("corruption_list 必须包含 33 个 0–255 整数字节")
    raw = decode_base64(b64_str)
    if len(raw) % 16:
        raise ValueError("Agilent 复数数据长度必须是 16 的倍数")
    result = bytearray(len(raw))
    for group in range(0, len(raw), 8):
        for byte_idx in range(8):
            target = group + byte_idx
            result[target] = raw[group + 7 - byte_idx] ^ mask[target % 33]
    return tuple_double_to_complex(result)
