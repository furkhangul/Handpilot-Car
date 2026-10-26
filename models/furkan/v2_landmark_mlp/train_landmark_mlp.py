"""HandPilot - el noktasi (landmark) tabanli MLP.

CNN modelindeki ile ayni kisi ayrimi kullanilir (../v1_cnn/reports/person_split.json):
egitim = 9 kisi, dogrulama = 4848, sbl1, test = 1333, hzl1.
Ozellikler: bilek (0) orijin, 0-9 mesafesine bolme, donme yok -> 63 koordinat + 13 geometrik ozellik.
"""
import json
import os
import sys
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import joblib
import keras
import numpy as np
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, precision_recall_fscore_support, roc_auc_score)
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight

HERE = Path(__file__).parent
LANDMARKS = Path(sys.argv[1])          # landmarks.npz (relpath, person, gesture, lm, n_hands)
CLASSES = ["gaz", "fren", "sol", "sag"]
SEED = 20261024
TIPS, MCPS = [4, 8, 12, 16, 20], [2, 5, 9, 13, 17]


def features(lm):
    rel = lm - lm[:, :1]
    n = rel / np.maximum(np.linalg.norm(rel[:, 9], axis=1), 1e-8)[:, None, None]
    tip, mcp = np.linalg.norm(n[:, TIPS], axis=2), np.linalg.norm(n[:, MCPS], axis=2)
    v = n[:, 4, :2] - n[:, 2, :2]
    v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-8)
    t = n[:, TIPS]
    pair = np.mean([np.linalg.norm(t[:, i] - t[:, j], axis=1) for i in range(5) for j in range(i + 1, 5)], axis=0)
    return np.hstack([n.reshape(len(n), -1), tip / np.maximum(mcp, 1e-8), tip, v[:, 1:2], v[:, :1], pair[:, None]])


d = np.load(LANDMARKS)
split = json.loads((HERE.parent / "v1_cnn/reports/person_split.json").read_text())["people"]
ok = d["n_hands"] >= 1
X = features(d["lm"][ok]).astype(np.float32)
y = np.array([CLASSES.index(g) for g in d["gesture"][ok]])
person = d["person"][ok]
part = {k: np.isin(person, split[k]) for k in ["train", "validation", "test"]}

scaler = StandardScaler().fit(X[part["train"]])
Xs = scaler.transform(X).astype(np.float32)

keras.utils.set_random_seed(SEED)
model = keras.Sequential([
    keras.Input((X.shape[1],)),
    keras.layers.Dense(128, kernel_regularizer=keras.regularizers.l2(1e-4)),
    keras.layers.BatchNormalization(), keras.layers.Activation("relu"), keras.layers.Dropout(0.3),
    keras.layers.Dense(64, kernel_regularizer=keras.regularizers.l2(1e-4)),
    keras.layers.BatchNormalization(), keras.layers.Activation("relu"), keras.layers.Dropout(0.3),
    keras.layers.Dense(4, activation="softmax"),
])
model.compile(optimizer=keras.optimizers.AdamW(1e-3, weight_decay=1e-4), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
cw = compute_class_weight("balanced", classes=np.arange(4), y=y[part["train"]])
hist = model.fit(Xs[part["train"]], y[part["train"]], validation_data=(Xs[part["validation"]], y[part["validation"]]),
                 epochs=200, batch_size=128, class_weight=dict(enumerate(cw)), verbose=0,
                 callbacks=[keras.callbacks.EarlyStopping("val_loss", patience=15, restore_best_weights=True),
                            keras.callbacks.ReduceLROnPlateau("val_loss", factor=0.5, patience=6)])


def evaluate(mask):
    p = model.predict(Xs[mask], verbose=0)
    yt, yp = y[mask], p.argmax(1)
    pr, rc, f1, sup = precision_recall_fscore_support(yt, yp, labels=range(4), zero_division=0)
    return {"n": int(mask.sum()), "accuracy": accuracy_score(yt, yp), "balanced_accuracy": balanced_accuracy_score(yt, yp),
            "macro_f1": f1_score(yt, yp, average="macro"), "roc_auc_macro_ovr": roc_auc_score(np.eye(4)[yt], p, average="macro"),
            "per_class": {c: {"precision": float(pr[i]), "recall": float(rc[i]), "f1": float(f1[i]), "support": int(sup[i])}
                          for i, c in enumerate(CLASSES)},
            "confusion_matrix": confusion_matrix(yt, yp, labels=range(4)).tolist(),
            "gaz_as_fren": int(((yt == 0) & (yp == 1)).sum()), "fren_as_gaz": int(((yt == 1) & (yp == 0)).sum())}


metrics = {"class_order": CLASSES, "split_people": split, "epochs_ran": len(hist.history["loss"]),
           "validation": evaluate(part["validation"]), "test": evaluate(part["test"])}
model.save(HERE / "landmark_mlp.keras")
joblib.dump(scaler, HERE / "scaler.joblib")
(HERE / "classes.json").write_text(json.dumps({"classes": CLASSES}, indent=2))
(HERE / "metrics.json").write_text(json.dumps(metrics, indent=2))
(HERE / "history.json").write_text(json.dumps({k: [float(v) for v in vs] for k, vs in hist.history.items()}, indent=2))
t = metrics["test"]
print(f"epochs={metrics['epochs_ran']} | test n={t['n']} acc={t['accuracy']:.4f} bal={t['balanced_accuracy']:.4f} "
      f"f1={t['macro_f1']:.4f} auc={t['roc_auc_macro_ovr']:.4f} | recall " +
      " ".join(f"{c}={t['per_class'][c]['recall']:.4f}" for c in CLASSES) + f" | gaz>fren={t['gaz_as_fren']} fren>gaz={t['fren_as_gaz']}")
print(f"val acc={metrics['validation']['accuracy']:.4f}")
