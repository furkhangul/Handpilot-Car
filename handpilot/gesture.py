"""4 modelin ortak kararı (ensemble) + geometrik kural kontrolü -> GestureResult.

Modeller: sinem (76 özellik MLP), reyyan (63 özellik MLP), sibel (CNN 160), hazal (CNN 192).
Hepsi TFLite ile çalışır (models/runtime, tools/export_models.py). Karar kuralı:
  - FREN: ağırlıklı ortalama >= CONF_FREN  VEYA  en az VOTES_FREN model fren diyor  (fren kazanır)
  - GAZ : en az VOTES_GAZ model gaz diyor ve onların ortalama güveni >= CONF_GAZ, kural: açık parmak <= 1, başparmak kapalı
  - YÖN : en az VOTES_TURN model aynı yönü diyor ve onların ortalama güveni >= CONF_TURN, kural (README §10.3, v5.1):
          4 parmak kapalı, başparmak açık, başparmak (2 -> 4) yataydan <= TURN_MAX_ANGLE_DEG, x yönü sınıfla aynı
  - GERİ: modellerde sınıfı yok, geometriden okunur: yumruk + başparmak AŞAĞI (👎)
  - aksi halde "diger" (controller önceki komutu korur, 1 sn sürerse durur)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np

from handpilot import config
from handpilot.features import features63, features76, fingers_open, thumb_direction, thumb_open
from handpilot.landmarks import Hand, crop_roi

try:
    from ai_edge_litert.interpreter import Interpreter
except ImportError:  # TensorFlow kuruluysa onun yorumlayıcısı da olur
    from tensorflow.lite.python.interpreter import Interpreter

C = config.CLASSES


@dataclass(frozen=True)
class GestureResult:
    hand_present: bool
    label: str                  # "gaz" | "fren" | "sol" | "sag" | "geri" | "diger" | "yok"
    confidence: float           # Ağırlıklı ortalama olasılık (seçilen sınıf)
    rule_ok: bool
    t: float
    probs: tuple[float, ...] = ()                 # config.CLASSES sırasında ortalama
    votes: dict = field(default_factory=dict)     # model adı -> o modelin seçtiği sınıf
    reason: str = ""


class _Model:
    def __init__(self, name: str) -> None:
        meta = json.loads((config.RUNTIME_DIR / f"{name}.json").read_text(encoding="utf-8"))
        self.name, self.kind = name, meta["input"]
        self.it = Interpreter(model_path=str(config.RUNTIME_DIR / f"{name}.tflite"), num_threads=2)
        self.it.allocate_tensors()
        self.i = self.it.get_input_details()[0]["index"]
        self.o = self.it.get_output_details()[0]["index"]
        self.order = [meta["classes"].index(c) for c in C]   # Modelin sırası -> ortak sıra
        self.size, self.padding = meta.get("size"), meta.get("padding")
        self.mean = np.array(meta["mean"], np.float32) if "mean" in meta else None
        self.scale = np.array(meta["scale"], np.float32) if "scale" in meta else None
        self.weight = config.MODEL_WEIGHTS[name]

    def predict(self, hand: Hand) -> np.ndarray | None:
        if self.kind == "roi":
            x = crop_roi(hand.rgb, hand.lm, self.size, self.padding)
            if x is None:
                return None
        else:
            f = features76(hand.lm) if self.kind == "features76" else features63(hand.lm)
            x = (f - self.mean) / self.scale
        self.it.set_tensor(self.i, x[None].astype(np.float32))
        self.it.invoke()
        return self.it.get_tensor(self.o)[0][self.order]


class GestureEnsemble:
    def __init__(self, names=None) -> None:
        self.models = [_Model(n) for n in (names or config.MODEL_WEIGHTS)]

    def classify(self, hand: Hand, t: float) -> GestureResult:
        if hand.count == 0:
            return GestureResult(False, "yok", 0.0, False, t, reason="el yok")
        if hand.count > 1:
            return GestureResult(True, "diger", 0.0, False, t, reason="birden fazla el")

        probs, weights, votes = [], [], {}
        for m in self.models:
            p = m.predict(hand)
            if p is not None:
                probs.append(p)
                weights.append(m.weight)
                votes[m.name] = C[int(np.argmax(p))]
        if not probs:
            return GestureResult(True, "diger", 0.0, False, t, reason="ROI yok")
        probs, weights = np.array(probs), np.array(weights)
        avg = np.average(probs, axis=0, weights=weights)
        tops = probs.argmax(axis=1)
        count = {c: int((tops == i).sum()) for i, c in enumerate(C)}
        best = C[int(np.argmax(avg))]
        p = dict(zip(C, avg.tolist()))

        def voters_conf(c):
            """O sınıfı seçen modellerin o sınıfa verdiği ağırlıklı ortalama olasılık."""
            i = C.index(c)
            m = tops == i
            return float(np.average(probs[m, i], weights=weights[m])) if m.any() else 0.0

        def result(label, rule_ok, reason=""):
            return GestureResult(True, label, p.get(label, float(avg.max())), rule_ok, t,
                                 tuple(avg.tolist()), votes, reason)

        if p["fren"] >= config.CONF_FREN or count["fren"] >= config.VOTES_FREN:
            return result("fren", True)

        opened = fingers_open(hand.lm, config.EXT_RATIO)
        fist = sum(opened.values()) == 0                      # 4 parmak kapalı
        thumb = thumb_open(hand.lm, config.EXT_RATIO)
        angle, dx, dy = thumb_direction(hand.lm, hand.rgb.shape[1] / hand.rgb.shape[0])
        if config.REVERSE_ENABLED and fist and thumb and dy > 0 and angle >= config.GERI_MIN_ANGLE_DEG:
            return GestureResult(True, "geri", 1.0 - p["fren"], True, t, tuple(avg.tolist()), votes, "başparmak aşağı")
        if best == "gaz":
            rule = sum(opened.values()) <= 1 and not thumb
            if voters_conf("gaz") >= config.CONF_GAZ and count["gaz"] >= config.VOTES_GAZ and rule:
                return result("gaz", True)
            return result("diger", rule, "gaz onaylanmadı")
        if best in ("sol", "sag"):
            side_ok = (dx < 0) if best == "sol" else (dx > 0)
            rule = fist and thumb and angle <= config.TURN_MAX_ANGLE_DEG and side_ok
            if voters_conf(best) >= config.CONF_TURN and count[best] >= config.VOTES_TURN and rule:
                return result(best, True)
            return result("diger", rule, f"{best} onaylanmadı")
        return result("diger", False, "düşük güven")
