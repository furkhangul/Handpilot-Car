#!/usr/bin/env python3
"""HandPilot-Car · Veri Toplama (tek dosya, arkadaşlara gönderilebilir)

Ne yapar?
    Kamerayı açar, her saniye 1 fotoğraf kaydeder. 4 hareketin her biri için 300 fotoğraf çeker:
    gaz, fren, sol, sag. Her 30 fotoğrafta bir mola verir. Ekranda yapılacak hareket, nasıl
    yapılacağına dair ipucu ve son kaydedilen fotoğraf görünür.

    Bütün hareketler SADECE SAĞ ELLE yapılır:
        gaz  = yumruk (başparmak parmakların üstünde)
        fren = açık avuç
        sol  = yumruk, başparmak ekranda sola bakar
        sag  = yumruk, başparmak ekranda sağa bakar

Nereye kaydeder?
    Masaüstü/HandPilot_Veri/
        gaz/   fren/   sol/   sag/        <- fotoğraflar, adları rastgele 8 karakter (örn. k3x9q2ma.jpg)
        kayit_<kod>.csv                   <- hangi fotoğraf kime ait, hangi tur (eğitimde gerekli!)

    Adlar rastgele olduğu için 8 kişinin klasörleri tek klasörde birleştirilebilir; aynı ad çıkmaz.
    Birleştirirken .csv dosyalarını da aynı klasöre kopyalayın (her kişinin kodu farklı olmalı).

Kurulum (bir kez):
    pip install opencv-python

Çalıştırma:
    python veri_topla.py
    (macOS ilk açılışta: Sistem Ayarları > Gizlilik ve Güvenlik > Kamera > Terminal'e izin ver)

Tuşlar (kamera penceresi seçiliyken):
    SPACE  başla / molayı geç        P  duraklat / devam
    R      turu baştan çek           S  bu hareketi atla, sıradakine geç (her ekranda)
    Q/ESC  kaydet ve çık

S ile atlamak: Bir hareketi daha önce bitirdiysen (örn. gaz) S'ye bas, frene geçer; tekrar S,
sola geçer... Çekim sırasında S'ye basılırsa yarım tur silinir, molada basılırsa biten tur kaydedilir.

Yarıda kalırsa tekrar çalıştırıp aynı kodu girin: kaldığı yerden devam eder.
"""

from __future__ import annotations

import csv
import math
import re
import secrets
import string
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import cv2
except ImportError:
    sys.exit("OpenCV bulunamadı. Önce şunu çalıştırın:  pip install opencv-python")

# ======================= AYARLAR (gerekirse buradan değiştirin) =======================
PHOTOS_PER_GESTURE = 300   # her hareket için fotoğraf sayısı
SECONDS_PER_PHOTO = 1.0    # kaç saniyede bir fotoğraf
PHOTOS_PER_ROUND = 30      # kaç fotoğrafta bir mola
REST_SECONDS = 20          # mola süresi
COUNTDOWN_SECONDS = 3      # her turdan önce geri sayım
CAMERA_INDEX = 0           # önce bu denenir; açılmazsa 1, 2 otomatik denenir. Yanlış kamera açılırsa 1 yapın
FRAME_W, FRAME_H = 640, 480
MIRROR = True              # selfie görüntüsü. Sürüş programıyla AYNI olmalı, değiştirmeyin
JPEG_QUALITY = 95
ROOT_FOLDER_NAME = "HandPilot_Veri"
# ======================================================================================

GESTURES = {
    "gaz": {
        "title": "GAZ = YUMRUK",
        "tips": [
            "4 parmak avuca kapalı, başparmak parmakların ÜSTÜNDE",
            "Başparmağı avucun İÇİNE sokma, YANA da çıkarma",
            "Parmak boğumları kameraya baksın, bilek düz",
        ],
    },
    "fren": {
        "title": "FREN = AÇIK AVUÇ",
        "tips": [
            "5 parmak tamamen açık ve ARALIKLI",
            "Avuç içi kameraya, parmaklar yukarı ('DUR' işareti)",
            "Parmakları birbirine yapıştırma",
        ],
    },
    "sol": {
        "title": "SOL = YUMRUK, BAŞPARMAK SOLA",
        "tips": [
            "4 parmak yumruk, başparmak dışarıda ve YATAY",
            "Başparmak ekranda SOLA baksın",
            "Başparmağı kameraya değil, YANA doğrult",
        ],
    },
    "sag": {
        "title": "SAĞ = YUMRUK, BAŞPARMAK SAĞA",
        "tips": [
            "4 parmak yumruk, başparmak dışarıda ve YATAY",
            "Başparmak ekranda SAĞA baksın",
            "Başparmağı kameraya değil, YANA doğrult",
        ],
    },
}

# Her tur farklı koşul: model farklı mesafe/konum/açıyı öğrensin.
ROUND_HINTS = [
    "Normal: el ekranın ortasında, yaklaşık 50 cm",
    "Yakın: yaklaşık 40 cm",
    "Uzak: yaklaşık 80 cm",
    "Eli ekranda yavaşça gezdir: sol-orta-sağ",
    "Eli ekranda yavaşça gezdir: yukarı-aşağı",
    "Bileği hafifçe sağa-sola çevir (hareketi bozmadan)",
    "Eli hafifçe öne-arkaya eğ (hareketi bozmadan)",
    "Normal ama kameraya biraz daha yakın/uzak gidip gel",
    "Işığa göre dur: yüzünü biraz pencereye/lambaya dön",
    "Serbest: hareketi bozmadan doğal şekilde oynat",
]

CSV_FIELDS = ["file", "gesture", "person", "computer_session", "round", "index",
              "timestamp", "width", "height", "mirrored", "hint"]

WINDOW = "HandPilot-Car Veri Toplama"
FONT = cv2.FONT_HERSHEY_SIMPLEX
GREEN, RED, YELLOW = (80, 220, 80), (60, 60, 230), (40, 210, 240)
WHITE, GREY = (255, 255, 255), (190, 190, 190)
K_QUIT, K_SPACE = {ord("q"), ord("Q"), 27}, {ord(" ")}
K_PAUSE, K_REDO, K_SKIP = {ord("p"), ord("P")}, {ord("r"), ord("R")}, {ord("s"), ord("S")}

NAME_CHARS = string.ascii_lowercase + string.digits  # küçük harf: Windows/macOS büyük-küçük ayırmaz
_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def ascii_tr(text: str) -> str:
    """cv2.putText Türkçe harf çizemez ('?' basar)."""
    return text.translate(_TR)


def put(img, text, org, scale=0.55, color=WHITE, thick=1):
    text = ascii_tr(text)
    x, y = org
    cv2.putText(img, text, (x + 2, y + 2), FONT, scale, (0, 0, 0), thick, cv2.LINE_AA)  # gölge
    cv2.putText(img, text, (x, y), FONT, scale, color, thick, cv2.LINE_AA)


def put_center(img, text, y, scale, color=WHITE, thick=2):
    (tw, _), _ = cv2.getTextSize(ascii_tr(text), FONT, scale, thick)
    put(img, text, ((img.shape[1] - tw) // 2, y), scale, color, thick)


def shade(img, y1, y2, strength=0.6):
    y1, y2 = max(0, y1), min(img.shape[0], y2)
    if y2 > y1:
        img[y1:y2] = cv2.convertScaleAbs(img[y1:y2], alpha=1.0 - strength, beta=0)


def find_desktop() -> Path:
    """Masaüstü klasörünü bulur (Windows OneDrive ve Türkçe 'Masaüstü' dahil), yoksa ana klasör."""
    home = Path.home()
    for c in [home / "Desktop", home / "OneDrive" / "Desktop", home / "OneDrive" / "Masaüstü",
              home / "Masaüstü", home / "Masaustu"]:
        if c.is_dir():
            return c
    return home


def random_name(folder: Path) -> str:
    while True:
        name = "".join(secrets.choice(NAME_CHARS) for _ in range(8)) + ".jpg"
        if not (folder / name).exists():
            return name


def ask_person() -> str:
    print("\nKatılımcı kodunu gir (örn. p01). Her kişinin kodu FARKLI olmalı.")
    print("Gerçek isim yerine kod kullan; kod-isim listesi ekip liderinde durur.")
    while True:
        code = ascii_tr(input("Kod: ").strip()).lower()
        if re.fullmatch(r"[a-z0-9_-]{1,20}", code):
            return code
        print("  Sadece harf, rakam, '-' ve '_' (örn. p01). Tekrar dene.")


class Collector:
    def __init__(self, person: str, root: Path):
        self.person = person
        self.root = root
        self.session = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.csv_path = root / f"kayit_{person}.csv"
        self.cap = None
        self.last_photo = None
        self.last_name = ""
        self.flash_until = 0.0
        self.current: list[tuple[Path, dict]] = []  # çekilen tur
        self.done: list[tuple[Path, dict]] = []     # biten, molada R ile silinebilir
        self.counts = self.load_counts()

    # ---------- kayıt ----------

    def load_counts(self) -> dict[str, int]:
        """Bu kişinin daha önce çektiklerini sayar (yarıda kalan oturuma devam için)."""
        counts = {g: 0 for g in GESTURES}
        if self.csv_path.exists():
            with self.csv_path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("gesture") in counts and (self.root / row["file"]).exists():
                        counts[row["gesture"]] += 1
        return counts

    def save(self, img, gesture: str, rnd: int, hint: str):
        folder = self.root / gesture
        name = random_name(folder)
        path = folder / name
        if not cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]):
            raise RuntimeError(f"Fotoğraf yazılamadı: {path}")
        row = {
            "file": f"{gesture}/{name}", "gesture": gesture, "person": self.person,
            "computer_session": self.session, "round": rnd,
            "index": self.counts[gesture] + len(self.current) + 1,
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "width": img.shape[1], "height": img.shape[0], "mirrored": int(MIRROR), "hint": hint,
        }
        self.last_photo, self.last_name = img, name
        return path, row

    @staticmethod
    def discard(items):
        for path, _ in items:
            path.unlink(missing_ok=True)
        items.clear()

    def accept(self):
        if not self.done:
            return
        new = not self.csv_path.exists()
        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if new:
                w.writeheader()
            for _, row in self.done:
                w.writerow(row)
                self.counts[row["gesture"]] += 1
        self.done = []

    # ---------- kamera / ekran ----------

    @staticmethod
    def try_camera(index: int, backend: int):
        """Kamerayı açar ve gerçekten kare verdiğini kontrol eder; olmazsa None."""
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened():
            cap.release()
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        for _ in range(30):  # ilk kareler boş/siyah gelebilir
            ok, img = cap.read()
            if ok and img is not None and img.size and img.max() > 0:
                return cap
            time.sleep(0.1)
        cap.release()
        return None

    def open_camera(self):
        if sys.platform == "darwin":
            backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        elif sys.platform.startswith("win"):
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]  # MSMF bazen çok yavaş açılır
        else:
            backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
        indexes = [CAMERA_INDEX] + [i for i in range(3) if i != CAMERA_INDEX]
        # macOS ilk açılışta izin sorar; izin verilene kadar kamera açılmaz, birkaç kez dene.
        for attempt in range(3):
            for index in indexes:
                for backend in backends:
                    cap = self.try_camera(index, backend)
                    if cap is not None:
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        print(f"Kamera açıldı: indeks {index}, {w}x{h}")
                        self.cap = cap
                        return
            if attempt < 2:
                print("Kamera açılamadı, tekrar deneniyor (izin penceresi çıktıysa İzin Ver'e bas)...")
                time.sleep(3)
        sys.exit(
            "Kamera açılamadı.\n"
            "  - Zoom/Teams/FaceTime gibi kamerayı kullanan programları kapat.\n"
            "  - macOS: Sistem Ayarları > Gizlilik ve Güvenlik > Kamera > Terminal'e\n"
            "    (VS Code'dan çalıştırıyorsan Visual Studio Code'a) izin ver, sonra terminali yeniden aç.\n"
            "  - Windows: Ayarlar > Gizlilik > Kamera > masaüstü uygulamalarına izin ver."
        )

    def frame(self):
        for _ in range(3):
            for _ in range(200):
                ok, img = self.cap.read()
                if ok and img is not None:
                    return cv2.flip(img, 1) if MIRROR else img
                cv2.waitKey(10)
            # Görüntü kesildi (başka program kamerayı aldı, iPhone kamerası koptu vb.): yeniden bağlan.
            print("Kamera görüntüsü kesildi, yeniden bağlanılıyor...")
            self.cap.release()
            time.sleep(1)
            self.open_camera()
        raise RuntimeError(
            "Kamera görüntü vermiyor. Kamerayı kullanan başka programları (Zoom, FaceTime, Teams) kapat;\n"
            "iPhone kamerası seçildiyse telefonu uzaklaştır veya CAMERA_INDEX değerini değiştir."
        )

    @staticmethod
    def show(img) -> int:
        cv2.imshow(WINDOW, img)
        return cv2.waitKey(1) & 0xFF

    def header(self, img, gesture, rnd=None, extra=""):
        shade(img, 0, 62)
        put(img, GESTURES[gesture]["title"], (12, 27), 0.75, YELLOW, 2)
        info = f"Kişi {self.person}  |  {self.counts[gesture] + len(self.current)}/{PHOTOS_PER_GESTURE} foto"
        if rnd is not None:
            info += f"  |  Tur {rnd}/{math.ceil(PHOTOS_PER_GESTURE / PHOTOS_PER_ROUND)}"
        put(img, info + extra, (12, 52), 0.5, GREY)

    def tips(self, img, gesture, hint=None):
        lines = list(GESTURES[gesture]["tips"])
        if hint:
            lines.append("Bu tur: " + hint)
        h = img.shape[0]
        top = h - 26 * len(lines) - 40
        shade(img, top - 8, h)
        for i, line in enumerate(lines):
            color = YELLOW if hint and i == len(lines) - 1 else WHITE
            put(img, ("- " if i < len(GESTURES[gesture]["tips"]) else "") + line,
                (12, top + 18 + 26 * i), 0.5, color)

    def keys_line(self, img, text):
        put(img, text, (12, img.shape[0] - 12), 0.45, GREY)

    def thumbnail(self, img):
        """Sağ üstte son kaydedilen fotoğraf."""
        if self.last_photo is None:
            return
        tw, th = 160, 120
        x, y = img.shape[1] - tw - 10, 70
        img[y:y + th, x:x + tw] = cv2.resize(self.last_photo, (tw, th))
        cv2.rectangle(img, (x - 1, y - 1), (x + tw, y + th), GREEN, 2)
        put(img, "Son kayit:", (x, y + th + 16), 0.42, GREEN)
        put(img, self.last_name, (x, y + th + 34), 0.42, GREEN)

    # ---------- ekranlar ----------

    def intro(self, gesture) -> str:
        left = PHOTOS_PER_GESTURE - self.counts[gesture]
        minutes = left * SECONDS_PER_PHOTO / 60 + (math.ceil(left / PHOTOS_PER_ROUND) - 1) * REST_SECONDS / 60
        while True:
            view = self.frame().copy()
            self.header(view, gesture)
            self.tips(view, gesture)
            put_center(view, "Hazir olunca SPACE", view.shape[0] // 2 - 20, 0.9, GREEN, 2)
            put_center(view, f"{left} foto kaldı, yaklaşık {minutes:.0f} dk", view.shape[0] // 2 + 15, 0.6, WHITE, 1)
            put_center(view, "SADECE SAĞ EL", view.shape[0] // 2 + 50, 0.7, RED, 2)
            self.keys_line(view, "SPACE: basla   S: bu hareketi atla (siradakine gec)   Q: cik")
            key = self.show(view)
            if key in K_SPACE:
                return "start"
            if key in K_SKIP:
                return "skip"
            if key in K_QUIT:
                return "quit"

    def capture_round(self, gesture, rnd, target) -> str:
        hint = ROUND_HINTS[(rnd - 1) % len(ROUND_HINTS)]
        end = time.monotonic() + COUNTDOWN_SECONDS
        while (left := end - time.monotonic()) > 0:
            view = self.frame().copy()
            self.header(view, gesture, rnd)
            self.tips(view, gesture, hint)
            put_center(view, "HAZIRLAN", view.shape[0] // 2 - 70, 1.0, YELLOW, 2)
            put_center(view, str(math.ceil(left)), view.shape[0] // 2 + 10, 2.5, YELLOW, 5)
            key = self.show(view)
            if key in K_QUIT:
                return "quit"
            if key in K_SKIP:
                return "skip"

        self.current = []
        next_shot, paused_at = time.monotonic(), None
        while len(self.current) < target:
            img = self.frame()
            now = time.monotonic()
            if paused_at is None and now >= next_shot:
                self.current.append(self.save(img, gesture, rnd, hint))
                self.flash_until = now + 0.15
                next_shot += SECONDS_PER_PHOTO
                if next_shot < now:  # takılma olduysa art arda çekme
                    next_shot = now + SECONDS_PER_PHOTO

            view = img.copy()  # kaydedilen kare temiz; yazılar sadece ekranda
            self.header(view, gesture, rnd, f"  |  bu tur {len(self.current)}/{target}")
            self.tips(view, gesture, hint)
            self.thumbnail(view)
            if now < self.flash_until:
                cv2.rectangle(view, (0, 0), (view.shape[1] - 1, view.shape[0] - 1), GREEN, 10)
            if paused_at is not None:
                put_center(view, "DURAKLATILDI (P)", view.shape[0] // 2, 1.1, RED, 3)
            self.keys_line(view, "P: duraklat   R: turu bastan al   S: hareketi atla   Q: kaydet ve cik")

            key = self.show(view)
            if key in K_QUIT:
                self.discard(self.current)
                return "quit"
            if key in K_REDO:
                self.discard(self.current)
                return "redo"
            if key in K_SKIP:
                self.discard(self.current)
                return "skip"
            if key in K_PAUSE:
                if paused_at is None:
                    paused_at = time.monotonic()
                else:
                    next_shot += time.monotonic() - paused_at
                    paused_at = None

        self.done, self.current = self.current, []
        return "done"

    def rest(self, gesture, rnd, finished_gesture) -> str:
        title = "HAREKET TAMAM!" if finished_gesture else "MOLA - ELINI DINLENDIR"
        end = time.monotonic() + REST_SECONDS
        while (left := end - time.monotonic()) > 0:
            view = self.frame().copy()
            shade(view, 0, view.shape[0], 0.55)
            self.header(view, gesture, rnd, f"  (+{len(self.done)} bu tur)")
            self.thumbnail(view)
            put_center(view, title, view.shape[0] // 2 - 40, 0.9, GREEN, 2)
            put_center(view, f"{math.ceil(left)} sn", view.shape[0] // 2 + 20, 1.6, WHITE, 3)
            if not finished_gesture:
                put_center(view, "Siradaki tur: " + ROUND_HINTS[rnd % len(ROUND_HINTS)],
                           view.shape[0] // 2 + 65, 0.5, YELLOW, 1)
            self.keys_line(view, "SPACE: devam   R: turu sil, tekrar cek   S: sonraki hareket   Q: kaydet ve cik")
            key = self.show(view)
            if key in K_SPACE:
                break
            if key in K_REDO:
                return "redo"
            if key in K_SKIP:
                return "skip"
            if key in K_QUIT:
                return "quit"
        return "next"

    # ---------- akış ----------

    def run(self):
        for g in GESTURES:
            (self.root / g).mkdir(parents=True, exist_ok=True)
        self.open_camera()
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        try:
            self._run()
        except KeyboardInterrupt:
            print("\nCtrl+C: çıkılıyor.")
        finally:
            self.discard(self.current)  # yarım tur kaydedilmez
            self.accept()
            self.cap.release()
            cv2.destroyAllWindows()
            self.summary()

    def _run(self):
        for gesture in GESTURES:
            if self.counts[gesture] >= PHOTOS_PER_GESTURE:
                print(f"  {gesture}: zaten {self.counts[gesture]} foto var, atlanıyor.")
                continue
            action = self.intro(gesture)
            if action == "quit":
                return
            if action == "skip":
                continue
            while self.counts[gesture] < PHOTOS_PER_GESTURE:
                rnd = self.counts[gesture] // PHOTOS_PER_ROUND + 1
                target = min(PHOTOS_PER_ROUND, PHOTOS_PER_GESTURE - self.counts[gesture])
                result = self.capture_round(gesture, rnd, target)
                if result == "quit":
                    return
                if result == "skip":
                    print(f"  {gesture}: S ile atlandı ({self.counts[gesture]}/{PHOTOS_PER_GESTURE}).")
                    break
                if result == "redo":
                    continue
                finished = self.counts[gesture] + len(self.done) >= PHOTOS_PER_GESTURE
                action = self.rest(gesture, rnd, finished)
                if action == "redo":
                    self.discard(self.done)
                    continue
                self.accept()
                if action == "quit":
                    return
                if action == "skip":
                    print(f"  {gesture}: S ile atlandı ({self.counts[gesture]}/{PHOTOS_PER_GESTURE}).")
                    break

    def summary(self):
        print(f"\nKayıt klasörü: {self.root}")
        for g in GESTURES:
            mark = "TAMAM" if self.counts[g] >= PHOTOS_PER_GESTURE else "eksik"
            print(f"  {g:<5} {self.counts[g]:>4}/{PHOTOS_PER_GESTURE}  {mark}")
        print(f"  Bilgi dosyası: {self.csv_path.name}  (fotoğraflarla birlikte gönder!)")
        if all(self.counts[g] >= PHOTOS_PER_GESTURE for g in GESTURES):
            print("\nHepsi tamam, teşekkürler! Klasörü ekip liderine gönderebilirsin.")
        else:
            print("\nEksik kaldı. Programı tekrar çalıştırıp AYNI kodu girersen kaldığı yerden devam eder.")


def main():
    root = find_desktop() / ROOT_FOLDER_NAME
    print("=" * 60)
    print(" HandPilot-Car · Veri Toplama")
    print(f" Hareket başına {PHOTOS_PER_GESTURE} foto, {SECONDS_PER_PHOTO:g} sn'de 1, "
          f"her {PHOTOS_PER_ROUND} fotoda {REST_SECONDS} sn mola")
    print(f" Kayıt yeri: {root}")
    print(" Bütün hareketler SADECE SAĞ ELLE yapılır.")
    print(" Bir hareketi bitirdiysen S ile atla, sıradakine geçer.")
    print("=" * 60)
    person = ask_person()
    root.mkdir(parents=True, exist_ok=True)
    Collector(person, root).run()


if __name__ == "__main__":
    main()
