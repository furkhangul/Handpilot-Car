"""Özellikler eğitim koduyla aynı mı, 4 model yükleniyor ve doğru sırada mı?"""

import json

import numpy as np
import pytest

from handpilot import config
from handpilot.features import features63, features76

TIPS, MCPS = [4, 8, 12, 16, 20], [2, 5, 9, 13, 17]


def train_features(lm):
    """models/furkan/v2_landmark_mlp/train_landmark_mlp.py içindeki fonksiyonun kopyası (Sinem ile aynı 76)."""
    rel = lm - lm[:, :1]
    n = rel / np.maximum(np.linalg.norm(rel[:, 9], axis=1), 1e-8)[:, None, None]
    tip, mcp = np.linalg.norm(n[:, TIPS], axis=2), np.linalg.norm(n[:, MCPS], axis=2)
    v = n[:, 4, :2] - n[:, 2, :2]
    v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-8)
    t = n[:, TIPS]
    pair = np.mean([np.linalg.norm(t[:, i] - t[:, j], axis=1) for i in range(5) for j in range(i + 1, 5)], axis=0)
    return np.hstack([n.reshape(len(n), -1), tip / np.maximum(mcp, 1e-8), tip, v[:, 1:2], v[:, :1], pair[:, None]])


def test_features_match_training_code():
    rng = np.random.default_rng(1)
    lms = rng.uniform(0, 1, size=(50, 21, 3)).astype(np.float32)
    ref = train_features(lms)
    ours = np.stack([features76(x) for x in lms])
    assert np.allclose(ours, ref, atol=1e-5)
    assert np.allclose(np.stack([features63(x) for x in lms]), ref[:, :63], atol=1e-5)


def test_scaler_means_are_plausible():
    """Sinem ve Reyyan scaler'larının ilk 63 ortalaması aynı formülü işaret etmeli."""
    s = json.loads((config.RUNTIME_DIR / "sinem.json").read_text())
    r = json.loads((config.RUNTIME_DIR / "reyyan.json").read_text())
    assert len(s["mean"]) == 76 and len(r["mean"]) == 63
    assert np.abs(np.array(s["mean"][:63]) - np.array(r["mean"])).max() < 0.1
    # Nokta 9 normalize edildiği için uzunluğu 1 olmalı
    assert np.linalg.norm(s["mean"][27:30]) == pytest.approx(1.0, abs=0.1)


def test_all_models_load_and_output_probabilities():
    from handpilot.gesture import GestureEnsemble
    from handpilot.landmarks import Hand

    ens = GestureEnsemble()
    assert {m.name for m in ens.models} == {"sinem", "reyyan", "sibel", "hazal"}
    rng = np.random.default_rng(2)
    lm = rng.uniform(0.3, 0.7, size=(21, 3)).astype(np.float32)
    rgb = rng.integers(0, 255, size=(480, 640, 3), dtype=np.uint8)
    hand = Hand(1, lm, rgb)
    for m in ens.models:
        p = m.predict(hand)
        assert p.shape == (4,) and abs(float(p.sum()) - 1) < 1e-3
    res = ens.classify(hand, 0.0)
    assert res.label in ("gaz", "fren", "sol", "sag", "diger")
    assert len(res.votes) == 4


def test_no_hand_and_two_hands():
    from handpilot.gesture import GestureEnsemble
    from handpilot.landmarks import Hand

    ens = GestureEnsemble(["reyyan"])
    assert ens.classify(Hand(0, None, None), 0).label == "yok"
    assert ens.classify(Hand(2, None, None), 0).label == "diger"
