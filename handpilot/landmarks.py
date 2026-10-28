"""MediaPipe el noktaları + CNN modelleri için el kırpma (ROI). MediaPipe yalnızca burada kullanılır."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps

from handpilot import config


@dataclass
class Hand:
    count: int                   # Karede bulunan el sayısı (0, 1, 2)
    lm: np.ndarray | None        # (21, 3) normalize koordinatlar; yalnızca tam 1 el varsa
    rgb: np.ndarray | None       # Aynalanmış RGB kare (ROI kırpmak için)


class HandTracker:
    def __init__(self) -> None:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        self._mp = mp
        self.connections = vision.HandLandmarksConnections.HAND_CONNECTIONS
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(config.HAND_TASK)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,  # İkinci el görünürse karar verilmez (güvenlik)
            min_hand_detection_confidence=config.DET_CONF,
            min_hand_presence_confidence=config.PRESENCE_CONF,
            min_tracking_confidence=config.TRACK_CONF,
        )
        self._det = vision.HandLandmarker.create_from_options(options)
        self._last_ms = -1

    def process(self, bgr: np.ndarray, t: float) -> Hand:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        ms = max(int(t * 1000), self._last_ms + 1)  # VIDEO modu artan zaman damgası ister
        self._last_ms = ms
        res = self._det.detect_for_video(self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb), ms)
        hands = res.hand_landmarks or []
        if len(hands) != 1:
            return Hand(len(hands), None, rgb)
        lm = np.array([(p.x, p.y, p.z) for p in hands[0]], dtype=np.float32)
        return Hand(1, lm, rgb)

    def close(self) -> None:
        self._det.close()


def crop_roi(rgb: np.ndarray, lm: np.ndarray, size: int, padding: float) -> np.ndarray | None:
    """Eğitimdeki kırpmanın aynısı: noktaların kutusu + %30 pay, siyah dolgu ile kare, bilinear."""
    h, w = rgb.shape[:2]
    pts = lm[:, :2] * np.array([w, h], dtype=np.float32)
    lo, hi = pts.min(0), pts.max(0)
    pad = float(max(hi - lo)) * padding
    box = (int(np.floor(lo[0] - pad)), int(np.floor(lo[1] - pad)),
           int(np.ceil(hi[0] + pad)), int(np.ceil(hi[1] + pad)))
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    roi = ImageOps.pad(Image.fromarray(rgb).crop(box), (size, size),
                       method=Image.Resampling.BILINEAR, color=(0, 0, 0))
    return np.asarray(roi, dtype=np.float32)
