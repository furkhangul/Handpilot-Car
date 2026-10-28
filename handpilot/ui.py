"""Ekrana çizim (FR-13). cv2.putText Türkçe harf çizemez, bu yüzden ASCII yazılır."""

from __future__ import annotations

import cv2

from handpilot import config

FONT = cv2.FONT_HERSHEY_SIMPLEX
COLORS = {"gaz": (60, 200, 60), "fren": (50, 50, 230), "sol": (230, 150, 40), "sag": (230, 150, 40),
          "geri": (0, 165, 255), "diger": (170, 170, 170), "yok": (120, 120, 120)}
TITLES = {"N": "DUZ", "L": "SOL", "R": "SAG"}
STATE_COLORS = {"DURUYOR": (50, 50, 230), "ILERI": (60, 200, 60), "GERI": (0, 165, 255), "YERINDE": (230, 150, 40)}


def _text(img, s, org, scale=0.55, color=(235, 235, 235), thick=1):
    cv2.putText(img, s, (org[0] + 1, org[1] + 1), FONT, scale, (0, 0, 0), thick + 1, cv2.LINE_AA)
    cv2.putText(img, s, org, FONT, scale, color, thick, cv2.LINE_AA)


def draw(img, hand, res, cmd, fps, link_ok, ping_ms, connections, car_enabled=True):
    h, w = img.shape[:2]
    if hand.lm is not None:
        pts = [(int(x * w), int(y * h)) for x, y, _ in hand.lm]
        for e in connections:
            cv2.line(img, pts[e.start], pts[e.end], (0, 220, 255), 2)
        for p in pts:
            cv2.circle(img, p, 3, (0, 255, 0), -1)

    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, 110), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

    state = cmd.mode if cmd.turn == "N" or not cmd.drive else f"{cmd.mode} - {TITLES[cmd.turn]}"
    _text(img, state, (14, 48), 1.3, STATE_COLORS[cmd.mode], 3)
    _text(img, f"El: {res.label.upper()}  guven {res.confidence:.2f}  {res.reason}", (14, 80), 0.55,
          COLORS.get(res.label, (235, 235, 235)))
    _text(img, "  ".join(f"{k}:{v}" for k, v in res.votes.items()), (14, 102), 0.45, (200, 200, 200))

    if car_enabled:
        net = f"WiFi OK {ping_ms:.0f} ms" if link_ok and ping_ms is not None else (
            "WiFi bekleniyor" if link_ok else "BAGLANTI YOK")
        color = (60, 200, 60) if link_ok and ping_ms is not None else (50, 50, 230)
    else:
        net, color = "ARAC KAPALI (--no-car)", (0, 200, 255)
    _text(img, f"FPS {fps:4.1f}", (w - 140, 30), 0.6,
          (60, 200, 60) if fps >= config.LOW_FPS else (50, 50, 230), 2)
    _text(img, net, (w - 260, 60), 0.55, color, 2)
    _text(img, "Q: cikis   SPACE: acil dur", (14, h - 12), 0.45, (210, 210, 210))

    if res.probs:
        for i, (name, p) in enumerate(zip(config.CLASSES, res.probs)):
            y = h - 120 + i * 22
            _text(img, name.upper(), (14, y + 14), 0.45)
            cv2.rectangle(img, (70, y), (230, y + 15), (90, 90, 90), 1)
            cv2.rectangle(img, (70, y), (70 + int(160 * p), y + 15), COLORS[name], -1)
