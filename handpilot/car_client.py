"""DriveCommand -> HTTP (README §11). Arka plan thread'i: ana döngü ağ yüzünden hiç beklemez.

Komut değişince HEMEN, değişmezse HEARTBEAT_S'de bir gönderilir. DUR oran sınırına takılmaz.
FAIL_LIMIT ardışık hata -> link_ok = False (controller aracı durdurur, kalkışa izin vermez).
"""

from __future__ import annotations

import threading
import time

import requests

from handpilot import config
from handpilot.controller import DriveCommand


class CarClient:
    def __init__(self, url: str = config.CAR_URL) -> None:
        self.url = url.rstrip("/")
        self._s = requests.Session()
        self._latest: DriveCommand | None = None
        self._sent: DriveCommand | None = None
        self._seq = 0
        self._fails = 0
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._times: list[float] = []
        self.ping_ms: float | None = None
        self._thread = threading.Thread(target=self._run, name="car_client", daemon=True)

    @property
    def link_ok(self) -> bool:
        return self._fails < config.FAIL_LIMIT

    def start(self) -> CarClient:
        self._thread.start()
        return self

    def set_latest(self, cmd: DriveCommand) -> None:
        """Bloklamaz. En son komut kazanır."""
        with self._lock:
            self._latest = cmd
        if cmd != self._sent:
            self._wake.set()

    def _send(self, cmd: DriveCommand) -> bool:
        self._seq += 1
        params = {"d": cmd.d, "s": cmd.speed, "t": cmd.turn, "seq": self._seq}
        t0 = time.perf_counter()
        try:
            r = self._s.get(f"{self.url}/cmd", params=params, timeout=config.HTTP_TIMEOUT_S)
            ok = r.status_code == 200
        except requests.RequestException:
            ok = False
        if ok:
            self.ping_ms = (time.perf_counter() - t0) * 1000
            self._fails = 0
        else:
            self._fails += 1
        return ok

    def _run(self) -> None:
        last = 0.0
        while not self._stop.is_set():
            self._wake.wait(config.HEARTBEAT_S)
            self._wake.clear()
            with self._lock:
                cmd = self._latest
            if cmd is None:
                continue
            now = time.monotonic()
            changed = cmd != self._sent
            if not changed and now - last < config.HEARTBEAT_S:
                continue
            self._times = [x for x in self._times if now - x < 1.0]
            if cmd.drive and len(self._times) >= config.MAX_REQ_PER_S:
                continue  # Oran sınırı; DUR hiç beklemez
            self._times.append(now)
            if self._send(cmd):
                self._sent = cmd
            last = now

    def close(self) -> None:
        """Programdan çıkarken: thread'i durdur, araca /stop gönder (FR-12)."""
        self._stop.set()
        self._wake.set()
        for _ in range(3):
            try:
                self._s.get(f"{self.url}/stop", timeout=config.HTTP_TIMEOUT_S)
                break
            except requests.RequestException:
                pass  # Yine de ESP32 watchdog'u 1 sn içinde durdurur
