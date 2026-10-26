"""Kisi bazli capraz dogrulama (leave-one-person-out).

Her katta bir kisi tamamen test icin ayrilir; kalan kisilerden ikisi dogrulama (early stopping),
digerleri egitim icin kullanilir. Model ve ozellikler train_landmark_mlp.py ile aynidir.
"""
import json
import os
import sys
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import keras
import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight

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


def build_model(n_features):
    m = keras.Sequential([
        keras.Input((n_features,)),
        keras.layers.Dense(128, kernel_regularizer=keras.regularizers.l2(1e-4)),
        keras.layers.BatchNormalization(), keras.layers.Activation("relu"), keras.layers.Dropout(0.3),
        keras.layers.Dense(64, kernel_regularizer=keras.regularizers.l2(1e-4)),
        keras.layers.BatchNormalization(), keras.layers.Activation("relu"), keras.layers.Dropout(0.3),
        keras.layers.Dense(4, activation="softmax"),
    ])
    m.compile(optimizer=keras.optimizers.AdamW(1e-3, weight_decay=1e-4),
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return m


HERE = Path(__file__).parent
d = np.load(sys.argv[1])
ok = d["n_hands"] >= 1
X = features(d["lm"][ok]).astype(np.float32)
y = np.array([CLASSES.index(g) for g in d["gesture"][ok]])
person = d["person"][ok]
people = sorted(set(person))
rng = np.random.default_rng(SEED)

folds, cm_total = [], np.zeros((4, 4), int)
for test_p in people:
    rest = [p for p in people if p != test_p]
    val_p = list(rng.choice(rest, 2, replace=False))
    tr, va, te = np.isin(person, [p for p in rest if p not in val_p]), np.isin(person, val_p), person == test_p
    sc = StandardScaler().fit(X[tr]); Xs = sc.transform(X).astype(np.float32)
    keras.utils.set_random_seed(SEED)
    m = build_model(X.shape[1])
    cw = compute_class_weight("balanced", classes=np.arange(4), y=y[tr])
    h = m.fit(Xs[tr], y[tr], validation_data=(Xs[va], y[va]), epochs=200, batch_size=128,
              class_weight=dict(enumerate(cw)), verbose=0,
              callbacks=[keras.callbacks.EarlyStopping("val_loss", patience=15, restore_best_weights=True),
                         keras.callbacks.ReduceLROnPlateau("val_loss", factor=0.5, patience=6)])
    yp = m.predict(Xs[te], verbose=0).argmax(1)
    cm_total += confusion_matrix(y[te], yp, labels=range(4))
    f = {"test_person": test_p, "validation_people": [str(p) for p in val_p], "n": int(te.sum()),
         "accuracy": accuracy_score(y[te], yp), "balanced_accuracy": balanced_accuracy_score(y[te], yp),
         "macro_f1": f1_score(y[te], yp, average="macro"), "epochs_ran": len(h.history["loss"])}
    folds.append(f)
    print(f"{test_p:8s} n={f['n']:5d} acc={f['accuracy']:.4f} f1={f['macro_f1']:.4f}", flush=True)

acc = np.array([f["accuracy"] for f in folds]); n = np.array([f["n"] for f in folds])
summary = {"folds": len(folds), "accuracy_mean": acc.mean(), "accuracy_std": acc.std(ddof=1),
           "accuracy_min": acc.min(), "accuracy_pooled": float((acc * n).sum() / n.sum()),
           "macro_f1_mean": float(np.mean([f["macro_f1"] for f in folds])),
           "balanced_accuracy_mean": float(np.mean([f["balanced_accuracy"] for f in folds])),
           "recall_pooled": {c: float(cm_total[i, i] / cm_total[i].sum()) for i, c in enumerate(CLASSES)},
           "confusion_matrix_pooled": cm_total.tolist()}
(HERE / "cv_metrics.json").write_text(json.dumps({"class_order": CLASSES, "summary": summary, "folds": folds}, indent=2, default=float))
print(json.dumps(summary, indent=1, default=float))
