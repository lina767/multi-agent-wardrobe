from __future__ import annotations

import math


def delta_e_lab(lab_a: tuple[float, float, float], lab_b: tuple[float, float, float]) -> float:
    dl = lab_a[0] - lab_b[0]
    da = lab_a[1] - lab_b[1]
    db = lab_a[2] - lab_b[2]
    return math.sqrt(dl * dl + da * da + db * db)


def harmony_from_delta_e(delta_e: float) -> float:
    return max(0.0, min(1.0, 1.0 - (delta_e / 100.0)))
