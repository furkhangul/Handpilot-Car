"""Tüm sayılar, eşikler ve adresler (README §13). Başka dosyaya sabit sayı yazılmaz."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------- Kamera ----------
CAMERA_INDEX = 0
FRAME_W, FRAME_H = 640, 480          # Modeller 640x480 kareyle eğitildi, değiştirme
MIRROR = True                        # veri_topla.py ile AYNI olmalı
LOW_FPS = 15

# ---------- MediaPipe ----------
HAND_TASK = ROOT / "models" / "runtime" / "hand_landmarker.task"
DET_CONF, PRESENCE_CONF, TRACK_CONF = 0.5, 0.5, 0.5

# ---------- Modeller (models/runtime, tools/export_models.py üretir) ----------
RUNTIME_DIR = ROOT / "models" / "runtime"
CLASSES = ("gaz", "fren", "sol", "sag")   # Ortak sınıf sırası
# Ağırlık: kişi bazlı testteki güvenilirliğe göre. Hazal (MobileNetV3 v1) "sol"
# sınıfında zayıf (recall %79,9; sol -> gaz karışması var), bu yüzden yarım ağırlık.
MODEL_WEIGHTS = {"sinem": 1.0, "reyyan": 1.0, "sibel": 1.0, "hazal": 0.5}

# ---------- Karar (ensemble) ----------
CONF_GAZ, CONF_TURN, CONF_FREN = 0.85, 0.75, 0.60   # Ağırlıklı ortalama olasılık
VOTES_GAZ, VOTES_TURN, VOTES_FREN = 3, 3, 2         # Bu sınıfı ilk sıraya koyan model sayısı
EXT_RATIO = 1.15                 # Parmak / başparmak açık eşiği (README §10.3; veriyle ayarlanır)
TURN_MAX_ANGLE_DEG = 35          # Yön için başparmağın (2 -> 4) yataydan en fazla sapması

# Geri (👎 yumruk + başparmak aşağı): modellerde "geri" sınıfı yok, geometriden okunur.
# 4 parmak kapalı, başparmak açık ve aşağıyı gösteriyor (yataydan en az bu kadar).
REVERSE_ENABLED = True
GERI_MIN_ANGLE_DEG = 55

# ---------- Onay ve zaman ----------
FRAMES_GAZ, FRAMES_TURN, FRAMES_FREN = 5, 3, 2
FRAMES_GERI, FRAMES_PIVOT = 5, 3
HELD_RELEASE_FRAMES = 2          # Geri / yerinde dönüş: hareket bu kadar kare görülmezse dur
HAND_LOST_STOP_S = 0.5
UNKNOWN_STOP_S = 1.0

# ---------- Hız ----------
SPEED_NORMAL = 180
SPEED_REVERSE = 150              # Geri yavaş: arkası görünmüyor
PIVOT_WHEN_STOPPED = True        # Duruyorken 👈/👉 = yerinde dönüş (tutulduğu sürece)
SPEED_PIVOT = 150

# ---------- Ağ ----------
CAR_URL = "http://192.168.4.1"
HTTP_TIMEOUT_S = 0.5
HEARTBEAT_S = 0.3
MAX_REQ_PER_S = 5
FAIL_LIMIT = 3

# ---------- Kayıt ----------
LOG_DIR = ROOT / "logs"
