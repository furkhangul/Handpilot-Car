"""21 el noktası -> modellerin beklediği özellik vektörleri (README §10.2).

Formüller ekibin eğitim kodlarıyla birebir aynıdır:
- features63: Reyyan (wrist0_middle9_l2_xyz_no_rotation_v1) ve Sinem'in ilk 63 sütunu
- features76: Sinem (handpilot_tasks_wrist_scale_76_v2) = 63 + 13 geometrik özellik
"""

from __future__ import annotations

import numpy as np

TIPS, MCPS = [4, 8, 12, 16, 20], [2, 5, 9, 13, 17]
EPS = 1e-8


def normalize(lm: np.ndarray) -> np.ndarray:
    """(21, 3) -> bilek orijinde, bilek->orta parmak kökü (9) mesafesi 1. Döndürme yok."""
    rel = lm - lm[0]
    return rel / max(float(np.linalg.norm(rel[9])), EPS)


def features63(lm: np.ndarray) -> np.ndarray:
    return normalize(lm).reshape(-1).astype(np.float32)


def features76(lm: np.ndarray) -> np.ndarray:
    n = normalize(lm)
    tip = np.linalg.norm(n[TIPS], axis=1)
    mcp = np.linalg.norm(n[MCPS], axis=1)
    v = n[4, :2] - n[2, :2]
    v = v / max(float(np.linalg.norm(v)), EPS)
    t = n[TIPS]
    pair = np.mean([np.linalg.norm(t[i] - t[j]) for i in range(5) for j in range(i + 1, 5)])
    extra = np.concatenate([tip / np.maximum(mcp, EPS), tip, [v[1], v[0], pair]])
    return np.concatenate([n.reshape(-1), extra]).astype(np.float32)


# ---------- Geometrik kural kontrolü (README §10.3, dönmeye dayanıklı) ----------

def fingers_open(lm: np.ndarray, ext_ratio: float) -> dict[str, bool]:
    """Parmak açık <=> |bilek->uç| / |bilek->PIP| > ext_ratio."""
    w = lm[0, :2]
    out = {}
    for name, tip, pip in (("index", 8, 6), ("middle", 12, 10), ("ring", 16, 14), ("pinky", 20, 18)):
        out[name] = np.linalg.norm(lm[tip, :2] - w) / max(np.linalg.norm(lm[pip, :2] - w), EPS) > ext_ratio
    return out


def thumb_open(lm: np.ndarray, ext_ratio: float) -> bool:
    """Başparmak açık <=> |uç (4) -> serçe kökü (17)| > |IP (3) -> serçe kökü| × ext_ratio (README §10.3)."""
    return bool(np.linalg.norm(lm[4, :2] - lm[17, :2]) > np.linalg.norm(lm[3, :2] - lm[17, :2]) * ext_ratio)


def thumb_direction(lm: np.ndarray, aspect: float) -> tuple[float, float, float]:
    """Başparmak (2 -> 4) vektörünün yataydan açısı (derece), x ve y yönü.

    aspect = genişlik / yükseklik; MediaPipe x ve y'yi ayrı ayrı 0..1'e böldüğü için düzeltilir.
    Aynalanmış karede x < 0 = ekranda sola; y > 0 = aşağı.
    """
    dx = (lm[4, 0] - lm[2, 0]) * aspect
    dy = lm[4, 1] - lm[2, 1]
    angle = float(np.degrees(np.arctan2(abs(dy), abs(dx))))
    return angle, float(dx), float(dy)
