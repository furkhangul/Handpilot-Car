"""Ekibin Keras modellerini canlı sürüş için TFLite'a çevirir (bir kez çalıştırılır).

Neden? Keras ile CNN çağrısı kare başına ~155 ms sürüyor; TFLite ile aynı çıktı 2-5 ms.
Scaler'lar JSON'a yazılır, böylece sürüşte TensorFlow / scikit-learn gerekmez.

Kullanım (TensorFlow kurulu ortamda):
    pip install tensorflow==2.21.0 keras==3.13.2 scikit-learn==1.6.1 joblib
    python tools/export_models.py

Çıktı: models/runtime/<ad>.tflite + <ad>.json + hand_landmarker.task
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import joblib
import keras
import numpy as np
import tensorflow as tf

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
OUT = MODELS / "runtime"
SIBEL_ZIP = MODELS / "sibel" / "HandPilot_CNN_Model_Paketi.zip"
SIBEL_MEMBER = "HandPilot_CNN_Model_Paketi/handpilot_mobilenet_v3_small.keras"

# Her modelin kendi sınıf sırası ve girdisi (eğitim kayıtlarından)
SPECS = {
    "sinem": {"file": MODELS / "sinem/best.keras", "scaler": MODELS / "sinem/scaler.joblib",
              "input": "features76", "classes": ["gaz", "fren", "sol", "sag"],
              "source": "models/sinem (MLP 128-64, handpilot_tasks_wrist_scale_76_v2)"},
    "reyyan": {"file": MODELS / "reyyan/best_mlp.keras", "scaler": MODELS / "reyyan/scaler.joblib",
               "input": "features63", "classes": ["gaz", "fren", "sol", "sag"],
               "source": "models/reyyan (MLP, wrist0_middle9_l2_xyz_no_rotation_v1)"},
    "sibel": {"file": None, "input": "roi", "size": 160, "padding": 0.30,
              "classes": ["fren", "gaz", "sag", "sol"],
              "source": "models/sibel zip (MobileNetV3Small, 160x160 RGB el ROI)"},
    "hazal": {"file": MODELS / "hazal/final_model.keras", "input": "roi", "size": 192, "padding": 0.30,
              "classes": ["fren", "gaz", "sag", "sol"],
              "source": "models/hazal (MobileNetV3Small, 192x192 RGB el ROI)"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def to_tflite(model) -> bytes:
    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    return conv.convert()


def check_same(model, tfl: bytes, shape) -> float:
    """TFLite çıktısı Keras ile aynı mı? (rastgele 8 girdi)"""
    it = tf.lite.Interpreter(model_content=tfl)
    it.allocate_tensors()
    i, o = it.get_input_details()[0], it.get_output_details()[0]
    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(8):
        x = rng.normal(size=(1, *shape)).astype(np.float32)
        if len(shape) == 3:
            x = rng.uniform(0, 255, size=(1, *shape)).astype(np.float32)
        it.set_tensor(i["index"], x)
        it.invoke()
        worst = max(worst, float(np.abs(it.get_tensor(o["index"]) - model(x, training=False).numpy()).max()))
    return worst


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(SIBEL_ZIP) as z:
        z.extract(SIBEL_MEMBER, tmp)
    SPECS["sibel"]["file"] = tmp / SIBEL_MEMBER

    for name, spec in SPECS.items():
        model = keras.models.load_model(spec["file"], compile=False)
        shape = tuple(model.input_shape[1:])
        tfl = to_tflite(model)
        diff = check_same(model, tfl, shape)
        if diff > 1e-4:
            sys.exit(f"{name}: TFLite çıktısı Keras'tan farklı (fark {diff:.2e}), durduruldu.")
        (OUT / f"{name}.tflite").write_bytes(tfl)
        meta = {k: v for k, v in spec.items() if k not in ("file", "scaler")}
        meta.update({"input_shape": list(shape), "keras_sha256": sha256(Path(spec["file"])),
                     "tflite_max_diff": diff})
        if "scaler" in spec:
            sc = joblib.load(spec["scaler"])
            if sc.n_features_in_ != shape[0]:
                sys.exit(f"{name}: scaler {sc.n_features_in_} özellik, model {shape[0]} bekliyor.")
            meta["mean"], meta["scale"] = sc.mean_.tolist(), sc.scale_.tolist()
        (OUT / f"{name}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{name:7s} {shape} -> {name}.tflite ({len(tfl) // 1024} KB), Keras farkı {diff:.1e}")

    shutil.copy(MODELS / "sinem/hand_landmarker_float16_v1.task", OUT / "hand_landmarker.task")
    shutil.rmtree(tmp, ignore_errors=True)
    print("Tamam:", OUT)


if __name__ == "__main__":
    main()
