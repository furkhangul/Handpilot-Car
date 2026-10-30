"""car_client: değişince hemen gönderir, heartbeat tekrarlar, hata sayar, çıkışta /stop yollar."""

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

from handpilot.car_client import CarClient
from handpilot.controller import DriveCommand


class FakeCar(BaseHTTPRequestHandler):
    log: ClassVar[list] = []

    def do_GET(self):
        u = urlparse(self.path)
        FakeCar.log.append((time.monotonic(), u.path, {k: v[0] for k, v in parse_qs(u.query).items()}))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":1}')

    def log_message(self, *a):
        pass


def server():
    srv = HTTPServer(("127.0.0.1", 0), FakeCar)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_send_heartbeat_and_stop():
    FakeCar.log = []
    srv = server()
    c = CarClient(f"http://127.0.0.1:{srv.server_port}").start()
    c.set_latest(DriveCommand(1, 180, "N", "x"))
    time.sleep(0.05)
    assert FakeCar.log and FakeCar.log[0][2]["d"] == "1"
    time.sleep(1.0)
    cmds = [x for x in FakeCar.log if x[1] == "/cmd"]
    assert 3 <= len(cmds) <= 6           # ~300 ms heartbeat
    seqs = [int(x[2]["seq"]) for x in cmds]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    t_change = time.monotonic()
    c.set_latest(DriveCommand(0, 0, "N", "palm"))
    time.sleep(0.05)
    stop = [x for x in FakeCar.log if x[1] == "/cmd" and x[2]["d"] == "0"]
    assert stop and stop[0][0] - t_change < 0.05   # Değişince hemen
    c.close()
    assert FakeCar.log[-1][1] == "/stop"
    assert c.link_ok
    srv.shutdown()


def test_link_lost_when_car_absent():
    c = CarClient("http://127.0.0.1:9").start()   # Kapalı port
    c.set_latest(DriveCommand(1, 180, "N", "x"))
    time.sleep(1.5)
    assert not c.link_ok
    c._stop.set()
