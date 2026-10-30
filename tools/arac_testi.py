"""Araç hareket testi: ileri, geri, sol, sağ, kavisler sırayla denenir (kamera / model gerekmez).

Her adımda tekerlerin ne yapması GEREKTİĞİ ekrana yazılır. Tutmuyorsa:
  - Bir teker ters dönüyor     -> firmware/handpilot_esp32/config.h: INVERT_LEFT / INVERT_RIGHT = 1
  - Sol ve sağ yer değiştirmiş -> motor kablolarını TB6612'de A <-> B değiştirin (ya da pinleri)
  - Teker hiç dönmüyor         -> MIN_PWM'i artırın, STBY / VM / sigortayı kontrol edin

Kullanım (laptop HandPilot-Car WiFi'ında, araç TEKERLERİ HAVADA):
    python tools/arac_testi.py
    python tools/arac_testi.py --sure 2 --hiz 200
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from handpilot import config

STEPS = [
    ("ILERI",          1, "N", "iki teker de İLERİ, aynı hızda"),
    ("GERI",          -1, "N", "iki teker de GERİ"),
    ("YERINDE SOL",    0, "L", "sol teker GERİ, sağ teker İLERİ (araç sola döner)"),
    ("YERINDE SAG",    0, "R", "sol teker İLERİ, sağ teker GERİ (araç sağa döner)"),
    ("ILERI + SOL",    1, "L", "ikisi de ileri, SOL teker yavaş"),
    ("ILERI + SAG",    1, "R", "ikisi de ileri, SAĞ teker yavaş"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=config.CAR_URL)
    ap.add_argument("--sure", type=float, default=1.5, help="her adımın süresi (sn)")
    ap.add_argument("--hiz", type=int, default=config.SPEED_NORMAL)
    a = ap.parse_args()
    s = requests.Session()
    try:
        print("Bağlantı:", s.get(a.url, timeout=2).text.strip())
        print("Durum   :", s.get(f"{a.url}/status", timeout=2).text.strip())
    except requests.RequestException as e:
        sys.exit(f"Araca ulaşılamadı ({a.url}). Laptop 'HandPilot-Car' WiFi'ında mı? {e}")

    seq = 1
    try:
        for name, d, t, expect in STEPS:
            input(f"\n[{name}] Beklenen: {expect}\n  Başlatmak için ENTER (Ctrl+C çıkış) ")
            end = time.monotonic() + a.sure
            while time.monotonic() < end:  # 200 ms'de bir yolla: watchdog durdurmasın
                r = s.get(f"{a.url}/cmd", params={"d": d, "s": a.hiz, "t": t, "seq": seq}, timeout=0.5)
                seq += 1
                if r.status_code != 200 or not r.json().get("ok"):
                    print("  Araç reddetti:", r.text)
                    break
                time.sleep(0.2)
            s.get(f"{a.url}/stop", timeout=0.5)
            print("  Durdu. Tutuyor muydu? (değilse dosyanın başındaki çözümlere bakın)")
    except KeyboardInterrupt:
        pass
    finally:
        try:
            s.get(f"{a.url}/stop", timeout=0.5)
        except requests.RequestException:
            pass  # Watchdog yine 1 sn içinde durdurur
        print("\nBitti, araç durduruldu.")


if __name__ == "__main__":
    main()
