"""Ortak karar kuralları (README §10.3, v5.1): sahte model olasılıkları + elle kurulmuş el noktaları."""

import numpy as np

from handpilot import config
from handpilot.gesture import GestureEnsemble
from handpilot.landmarks import Hand

RGB = np.zeros((480, 480, 3), np.uint8)  # Kare kare: açılar en-boy düzeltmesinden etkilenmesin

# Başparmağı +x yönüne uzanan yumruk (bilek altta, 4 parmak kıvrık). Satır = nokta numarası.
FIST_THUMB_OUT = np.array([
    [0.000, 0.10],                                            # 0 bilek
    [0.050, 0.07], [0.070, 0.03], [0.120, 0.03], [0.180, 0.03],  # 1-4 başparmak (dışarıda, yatay)
    [0.045, -0.05], [0.045, -0.10], [0.045, -0.08], [0.045, -0.03],   # 5-8 işaret (kıvrık)
    [0.015, -0.05], [0.015, -0.10], [0.015, -0.08], [0.015, -0.03],   # 9-12 orta
    [-0.015, -0.05], [-0.015, -0.10], [-0.015, -0.08], [-0.015, -0.03],  # 13-16 yüzük
    [-0.045, -0.05], [-0.045, -0.10], [-0.045, -0.08], [-0.045, -0.03],  # 17-20 serçe
])
FIST_THUMB_OVER = FIST_THUMB_OUT.copy()
FIST_THUMB_OVER[3], FIST_THUMB_OVER[4] = [0.070, 0.00], [0.030, -0.03]   # Başparmak parmakların üstünde


def hand(shape, direction=(1, 0)):
    """Şekli, başparmak `direction` yönünü gösterecek şekilde döndürür (y aşağı pozitif)."""
    a = np.arctan2(direction[1], direction[0])
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    lm = np.zeros((21, 3), np.float32)
    lm[:, :2] = shape @ rot.T + 0.5
    return Hand(1, lm, RGB)


LEFT, RIGHT, DOWN, UP = (-1, 0), (1, 0), (0, 1), (0, -1)


class Fake:
    def __init__(self, name, probs, weight=1.0):
        self.name, self.p, self.weight = name, np.array(probs, np.float32), weight

    def predict(self, hand):
        return self.p


def ensemble(*probs):
    e = GestureEnsemble.__new__(GestureEnsemble)
    e.models = [Fake(f"m{i}", p) for i, p in enumerate(probs)]
    return e


# config.CLASSES = (gaz, fren, sol, sag)
GAZ = [0.94, 0.02, 0.02, 0.02]
FREN = [0.02, 0.94, 0.02, 0.02]
SOL = [0.02, 0.02, 0.94, 0.02]
SAG = [0.02, 0.02, 0.02, 0.94]


def test_thumb_left_right():
    assert ensemble(SOL, SOL, SOL, SOL).classify(hand(FIST_THUMB_OUT, LEFT), 0).label == "sol"
    assert ensemble(SAG, SAG, SAG, SAG).classify(hand(FIST_THUMB_OUT, RIGHT), 0).label == "sag"


def test_model_says_left_but_thumb_points_right():
    assert ensemble(SOL, SOL, SOL, SOL).classify(hand(FIST_THUMB_OUT, RIGHT), 0).label == "diger"


def test_thumb_down_is_reverse_whatever_models_say():
    assert ensemble(SOL, SAG, SOL, GAZ).classify(hand(FIST_THUMB_OUT, DOWN), 0).label == "geri"


def test_thumb_up_is_nothing():
    assert ensemble(SOL, SOL, SAG, SAG).classify(hand(FIST_THUMB_OUT, UP), 0).label == "diger"


def test_gas_needs_thumb_closed_and_three_votes():
    assert ensemble(GAZ, GAZ, GAZ, SOL).classify(hand(FIST_THUMB_OVER, UP), 0).label == "gaz"
    assert ensemble(GAZ, GAZ, SOL, SOL).classify(hand(FIST_THUMB_OVER, UP), 0).label != "gaz"
    # Başparmak dışarıdaysa gaz değil (yön ya da geri ile karışmasın)
    assert ensemble(GAZ, GAZ, GAZ, GAZ).classify(hand(FIST_THUMB_OUT, LEFT), 0).label != "gaz"


def test_palm_votes_win():
    assert ensemble(FREN, FREN, GAZ, GAZ).classify(hand(FIST_THUMB_OUT, DOWN), 0).label == "fren"


def test_reverse_can_be_disabled(monkeypatch):
    monkeypatch.setattr(config, "REVERSE_ENABLED", False)
    assert ensemble(SOL, SOL, SAG, GAZ).classify(hand(FIST_THUMB_OUT, DOWN), 0).label != "geri"
