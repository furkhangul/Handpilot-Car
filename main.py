"""HandPilot-Car: kamera -> el noktaları -> 4 modelin ortak kararı -> durum makinesi -> WiFi -> araç.

Kullanım:
    python main.py                 # elle sür (laptop HandPilot-Car WiFi'ına bağlı olmalı)
    python main.py --no-car        # sadece tanıma testi, araca bir şey gönderilmez
    python main.py --keyboard      # kamerasız, klavyeyle sür (W ileri, S geri, A/D sol/sağ, SPACE dur)
    python main.py --models sinem,reyyan   # sadece seçilen modellerle
"""

from __future__ import annotations

import argparse
import atexit
import csv
import signal
import sys
import time
from datetime import datetime

import cv2

from handpilot import config
from handpilot.car_client import CarClient
from handpilot.controller import Controller, DriveCommand


def parse_args():
    ap = argparse.ArgumentParser(description="HandPilot-Car sürüş programı")
    ap.add_argument("--no-car", action="store_true", help="araca komut gönderme (tanıma testi)")
    ap.add_argument("--keyboard", action="store_true", help="kamerasız klavye modu")
    ap.add_argument("--camera", type=int, default=config.CAMERA_INDEX)
    ap.add_argument("--models", default=",".join(config.MODEL_WEIGHTS), help="virgülle model adları")
    ap.add_argument("--url", default=config.CAR_URL)
    return ap.parse_args()


def open_log():
    config.LOG_DIR.mkdir(exist_ok=True)
    f = (config.LOG_DIR / f"drive_{datetime.now():%Y%m%d_%H%M%S}.csv").open("w", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(["t_ms", "frame", "fps", "hand", "label", "conf", "rule_ok", "votes",
                "cmd_d", "cmd_s", "cmd_t", "reason", "link_ok", "ping_ms", "infer_ms"])
    return f, w


def keyboard_mode(car: CarClient | None) -> None:
    """FR-20 klavye modu (kamerasız araç testi).

    W ileri (mandallı) · SPACE dur · S basılı = geri · A/D basılı: giderken kavis, dururken yerinde dönüş · Q çıkış
    """
    import numpy as np

    from handpilot.ui import STATE_COLORS

    hold_s = 0.6                       # Klavye tekrarının ilk gecikmesini tolere eder
    win = "HandPilot - Klavye"
    cv2.namedWindow(win)
    forward = False
    held, held_t = "", 0.0
    while True:
        key = cv2.waitKey(30) & 0xFF
        now = time.monotonic()
        if key in (ord("q"), 27):
            break
        if key == ord(" "):
            forward, held = False, ""
        elif key == ord("w"):
            forward, held = True, ""
        elif key in (ord("a"), ord("d"), ord("s")):
            held, held_t = chr(key), now
        if held and now - held_t > hold_s:
            held = ""
        turn = {"a": "L", "d": "R"}.get(held, "N")
        if forward:
            cmd = DriveCommand(1, config.SPEED_NORMAL, turn, "key_forward")
        elif held == "s":
            cmd = DriveCommand(-1, config.SPEED_REVERSE, "N", "key_reverse")
        elif held in ("a", "d"):
            cmd = DriveCommand(0, config.SPEED_PIVOT, turn, "key_pivot")
        else:
            cmd = DriveCommand(0, 0, "N", "key_stop")
        if car:
            car.set_latest(cmd)

        img = np.zeros((220, 560, 3), np.uint8)
        state = cmd.mode if turn == "N" or not cmd.drive else f"{cmd.mode} {turn}"
        cv2.putText(img, state, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.4, STATE_COLORS[cmd.mode], 3)
        link = "yok" if car is None else ("OK" if car.link_ok else "BAGLANTI YOK")
        cv2.putText(img, f"WiFi: {link}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 220, 220), 2)
        cv2.putText(img, "W ileri  S geri  A/D sol/sag  SPACE dur  Q cikis", (20, 190),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.imshow(win, img)
    if car:
        car.set_latest(DriveCommand(0, 0, "N", "exit"))
    cv2.destroyAllWindows()


def main() -> None:
    args = parse_args()
    car = None if args.no_car else CarClient(args.url).start()

    def shutdown(*_):
        if car:
            car.close()
    atexit.register(shutdown)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    if args.keyboard:
        keyboard_mode(car)
        return

    from handpilot import ui
    from handpilot.gesture import GestureEnsemble
    from handpilot.landmarks import HandTracker

    names = [n.strip() for n in args.models.split(",") if n.strip()]
    ensemble = GestureEnsemble(names)
    tracker = HandTracker()
    ctrl = Controller()
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        sys.exit("Kamera açılamadı (macOS: Sistem Ayarları > Gizlilik ve Güvenlik > Kamera).")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_H)
    logf, log = open_log()
    win = "HandPilot-Car"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    t_start, last, fps, frame_no = time.monotonic(), time.monotonic(), 0.0, 0
    print("Modeller:", ", ".join(m.name for m in ensemble.models))
    try:
        while True:
            ok, img = cap.read()
            if not ok:
                print("Kameradan kare okunamadı.")
                break
            if config.MIRROR:
                img = cv2.flip(img, 1)
            now = time.monotonic()
            t0 = time.perf_counter()
            hand = tracker.process(img, now - t_start)
            res = ensemble.classify(hand, now)
            infer_ms = (time.perf_counter() - t0) * 1000
            link_ok = car.link_ok if car else True
            cmd = ctrl.update(res, link_ok)
            if car:
                car.set_latest(cmd)

            frame_no += 1
            fps = 0.9 * fps + 0.1 / max(now - last, 1e-6) if fps else 1 / max(now - last, 1e-6)
            last = now
            ping = car.ping_ms if car else None
            log.writerow([int((now - t_start) * 1000), frame_no, f"{fps:.1f}", hand.count, res.label,
                          f"{res.confidence:.3f}", int(res.rule_ok), "|".join(f"{k}={v}" for k, v in res.votes.items()),
                          cmd.d, cmd.speed, cmd.turn, cmd.reason, int(link_ok),
                          "" if ping is None else f"{ping:.0f}", f"{infer_ms:.1f}"])
            ui.draw(img, hand, res, cmd, fps, link_ok, ping, tracker.connections, car is not None)
            cv2.imshow(win, img)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord(" "):
                cmd = ctrl.exit()
                if car:
                    car.set_latest(cmd)
    finally:
        cmd = ctrl.exit()
        if car:
            car.set_latest(cmd)
        shutdown()
        cap.release()
        tracker.close()
        logf.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
