"""Sürüş durum makinesi (README §3): onay sayaçları, yön mandalı, zaman aşımları.

Hareket modları (hareket seti v2, web arayüzüyle aynı):
    DURUYOR   motorlar kapalı
    ILERI     ✊ 5 kare -> MANDALLI ileri
    GERI      ✋ açık avuç 2 kare -> MANDALLI yavaş geri
    YERINDE   (PIVOT_WHEN_STOPPED açıksa) duruyorken ⬅️/➡️ 3 kare -> yerinde dönüş, YALNIZCA tutulduğu sürece
Giderken ⬅️/➡️ (başparmak) kavis çizer; o anki yönün hareketi (✊ ya da ✋) düze döndürür.
Giderken ✊ ileriye, ✋ geriye geçirir. Durdurma hareketi yok: el 0,5 sn görünmezse, hareket 1 sn
belirsiz kalırsa ya da bağlantı koparsa araç durur. Klavyede SPACE acil durdurur.

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
TURN_OF = {"sol": "L", "sag": "R"}
DIR_OF = {"gaz": 1, "geri": -1}
REASON_OF = {1: "fist_confirmed", -1: "palm_reverse"}


def _frames(label: str) -> int:
    return config.FRAMES_GAZ if label == "gaz" else config.FRAMES_GERI


def _speed(d: int) -> int:
    return config.SPEED_NORMAL if d == 1 else config.SPEED_REVERSE


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
        self._streak = 0  # Durduktan sonra her hareket baştan onaylanır
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

        # 1) Tutma modu (yerinde dönüş): bırakılınca dur
        if self._held:
            if r.label == self._held:
                self._miss = 0
                return self.cmd
            self._miss += 1
            if self._miss >= config.HELD_RELEASE_FRAMES:
                return self._stop("released")
            return self.cmd

        # 2) El kaybı
        if r.label == "yok":
            if self._last_hand_t is None or r.t - self._last_hand_t >= config.HAND_LOST_STOP_S:
                return self._stop("hand_lost") if self.driving else self.cmd
            return self.cmd

        # 3) Giderken (ileri ya da geri)
        if self.driving:
            if r.label in DIR_OF:
                self._unknown_since = None
                d = DIR_OF[r.label]
                if d != self.cmd.d:  # ✊ <-> ✋: yön değiştir
                    if self._streak >= _frames(r.label):
                        return self._set(d, _speed(d), "N", REASON_OF[d])
                    return self.cmd
                if self._streak >= config.FRAMES_TURN and self.cmd.turn != "N":
                    return self._set(d, _speed(d), "N", "straight")
                return self.cmd
            if r.label in TURN_OF:
                self._unknown_since = None
                if self._streak >= config.FRAMES_TURN and TURN_OF[r.label] != self.cmd.turn:
                    return self._set(self.cmd.d, _speed(self.cmd.d), TURN_OF[r.label], f"turn_{r.label}")
                return self.cmd
            if self._unknown_since is None:  # diger: belirsiz say
                self._unknown_since = r.t
            if r.t - self._unknown_since >= config.UNKNOWN_STOP_S:
                return self._stop("unknown_timeout")
            return self.cmd

        # 4) Duruyorken: ileri, geri, yerinde dönüş
        self._unknown_since = None
        if r.label in DIR_OF and self._streak >= _frames(r.label):
            d = DIR_OF[r.label]
            return self._set(d, _speed(d), "N", REASON_OF[d])
        if r.label in TURN_OF and config.PIVOT_WHEN_STOPPED and self._streak >= config.FRAMES_PIVOT:
            return self._set(0, config.SPEED_PIVOT, TURN_OF[r.label], f"pivot_{r.label}", held=r.label)
        return self.cmd

    def exit(self) -> DriveCommand:
        return self._stop("exit")
