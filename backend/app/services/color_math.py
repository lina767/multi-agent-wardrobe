from __future__ import annotations

import math


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = [v / 255.0 for v in rgb]
    r = _pivot_rgb(r)
    g = _pivot_rgb(g)
    b = _pivot_rgb(b)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505
    x /= 0.95047
    z /= 1.08883
    x = _pivot_xyz(x)
    y = _pivot_xyz(y)
    z = _pivot_xyz(z)
    l = max(0.0, 116 * y - 16)
    a = 500 * (x - y)
    b2 = 200 * (y - z)
    return (l, a, b2)


def delta_e_lab(lab_a: tuple[float, float, float], lab_b: tuple[float, float, float]) -> float:
    dl = lab_a[0] - lab_b[0]
    da = lab_a[1] - lab_b[1]
    db = lab_a[2] - lab_b[2]
    return math.sqrt(dl * dl + da * da + db * db)


def harmony_from_delta_e(delta_e: float) -> float:
    return max(0.0, min(1.0, 1.0 - (delta_e / 100.0)))


def _pivot_rgb(value: float) -> float:
    if value > 0.04045:
        return ((value + 0.055) / 1.055) ** 2.4
    return value / 12.92


def _pivot_xyz(value: float) -> float:
    if value > 0.008856:
        return value ** (1.0 / 3.0)
    return (7.787 * value) + (16 / 116)
