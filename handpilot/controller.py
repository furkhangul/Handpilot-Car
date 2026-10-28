"""Sürüş durum makinesi (README §3): onay sayaçları, gaz mandalı, zaman aşımları.

Dört hareket modu:
    DURUYOR   motorlar kapalı
    ILERI     ✊ 5 kare -> MANDALLI ileri; giderken ⬅️/➡️ (başparmak) kavis, ✊ düz; ✋ ile durur
    GERI      duruyorken 👎 (yumruk + başparmak aşağı) 5 kare -> yavaş geri, YALNIZCA tutulduğu sürece
    YERINDE   duruyorken ⬅️/➡️ 3 kare -> yerinde dönüş, YALNIZCA tutulduğu sürece
✋ açık el (2 kare) her moddan durdurur. Tutma modlarında başka bir şey 2 kare görülürse durur.

Saf mantık: kamera, ağ, MediaPipe yok. Zaman dışarıdan gelir (r.t), bu yüzden test edilebilir.
"""

from __future__ import annotations

from dataclasses import dataclass

from handpilot import config


@dataclass(frozen=True)
class DriveCommand:
    d: int           # 1 ileri, -1 geri, 0 ilerlemiyor (speed > 0 ise yerinde dönüş)
    speed: int       # 0..255
    turn: str        # "N" | "L" | "R"
    reason: str

    @property
    def drive(self) -> bool:
        """Motorlar dönüyor mu?"""
        return self.speed > 0

    @property
    def mode(self) -> str:
        if not self.drive:
            return "DURUYOR"
        return {1: "ILERI", -1: "GERI", 0: "YERINDE"}[self.d]


STOP = DriveCommand(0, 0, "N", "init")
TURN_OF = {"sol": "L", "sag": "R", "gaz": "N"}


class Controller:
    def __init__(self) -> None:
        self.cmd = STOP
        self._label, self._streak = "", 0
        self._miss = 0                       # Tutma modunda tutulan hareketten farklı kare sayısı
        self._held = ""                      # Tutma modunda tutulması gereken etiket
        self._last_hand_t: float | None = None
        self._unknown_since: float | None = None

    @property
    def driving(self) -> bool:
        return self.cmd.drive

    def _set(self, d: int, speed: int, turn: str, reason: str, held: str = "") -> DriveCommand:
        self.cmd = DriveCommand(d, speed, turn, reason)
        self._held, self._miss = held, 0
        return self.cmd

    def _stop(self, reason: str) -> DriveCommand:
        self._unknown_since = None
        self._streak = 0  # Durduktan sonra her hareket baştan onaylanır (ileri -> dur -> geri zinciri olmaz)
        return self._set(0, 0, "N", reason)

    def update(self, r, link_ok: bool = True) -> DriveCommand:
        """r: GestureResult (label, t). link_ok: araçla bağlantı var mı (car_client)."""
        if r.label == self._label:
            self._streak += 1
        else:
            self._label, self._streak = r.label, 1

        if not link_ok:  # Bağlantı yokken kalkış da olmaz
            return self._stop("link_lost") if self.driving else self.cmd

        if r.label != "yok":
            self._last_hand_t = r.t

        # 1) Fren her zaman ve her modda kazanır
        if r.label == "fren":
            if self._streak >= config.FRAMES_FREN and self.driving:
                return self._stop("palm")
            if not self._held:
                return self.cmd

        # 2) Tutma modları (geri, yerinde dönüş): bırakılınca dur
        if self._held:
            if r.label == self._held:
                self._miss = 0
                return self.cmd
            self._miss += 1
            if self._miss >= config.HELD_RELEASE_FRAMES:
                return self._stop("released")
            return self.cmd

        # 3) El kaybı
        if r.label == "yok":
            if self._last_hand_t is None or r.t - self._last_hand_t >= config.HAND_LOST_STOP_S:
                return self._stop("hand_lost") if self.driving else self.cmd
            return self.cmd

        # 4) İleri giderken
        if self.cmd.d == 1 and self.driving:
            if r.label not in TURN_OF:  # diger, geri: belirsiz say
                if self._unknown_since is None:
                    self._unknown_since = r.t
                if r.t - self._unknown_since >= config.UNKNOWN_STOP_S:
                    return self._stop("unknown_timeout")
                return self.cmd
            self._unknown_since = None
            if self._streak >= config.FRAMES_TURN and TURN_OF[r.label] != self.cmd.turn:
                return self._set(1, config.SPEED_NORMAL, TURN_OF[r.label], f"turn_{r.label}")
            return self.cmd

        # 5) Duruyorken: kalkış, geri, yerinde dönüş
        self._unknown_since = None
        if r.label == "gaz" and self._streak >= config.FRAMES_GAZ:
            return self._set(1, config.SPEED_NORMAL, "N", "fist_confirmed")
        if r.label == "geri" and config.REVERSE_ENABLED and self._streak >= config.FRAMES_GERI:
            return self._set(-1, config.SPEED_REVERSE, "N", "reverse", held="geri")
        if r.label in ("sol", "sag") and config.PIVOT_WHEN_STOPPED and self._streak >= config.FRAMES_PIVOT:
            return self._set(0, config.SPEED_PIVOT, TURN_OF[r.label], f"pivot_{r.label}", held=r.label)
        return self.cmd

    def exit(self) -> DriveCommand:
        return self._stop("exit")
