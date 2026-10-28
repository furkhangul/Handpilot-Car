# ESP32'ye yükleme ve ilk sürüş

Bu rehber üç adımı anlatır: **(1)** firmware'i ESP32'ye yüklemek, **(2)** aracı telefondan, test aracıyla ve klavyeden denemek, **(3)** elle sürmek.

## Hareketler

| El | Araç | Nasıl çalışır |
|---|---|---|
| ✊ Yumruk (başparmak üstte) | **İLERİ** | 5 kare onaylanınca kalkar, **mandallıdır**: el değişse de ✋ gelene kadar gider |
| ⬅️ / ➡️ Yumruk, başparmak sola / sağa | Giderken **kavis** · dururken **yerinde dönüş** | Kavis: iç teker %40. Yerinde dönüş: tekerler zıt yönde, **tuttuğun sürece** |
| 👎 Yumruk, başparmak aşağı | **GERİ** | Yalnızca dururken, **tuttuğun sürece**, yavaş (150). İleri giderken 👎 aracı geri almaz, 1 sn sonra durdurur |
| ✋ Açık avuç | **DUR** | Her durumda kazanır (2 kare) |
| El yok / başka hareket | Güvenli durum | İleri giderken 0,5 sn el yoksa ya da 1 sn belirsizse durur; geri / yerinde dönüşte 2 karede durur |

Durduktan sonra her hareket baştan onaylanır: ileri → dur → geri zinciri kendiliğinden olmaz.

---

## 1. Firmware'i ESP32'ye yükleme (Arduino IDE 2)

### 1.1 Bir kez yapılacaklar

1. **Arduino IDE 2**'yi indirip kurun: <https://www.arduino.cc/en/software>
2. IDE'de **Ayarlar** (macOS: *Arduino IDE → Settings*, Windows: *File → Preferences*) → **Additional boards manager URLs** kutusuna şunu yapıştırın:
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
3. Sol menüde **Boards Manager** (kart simgesi) → `esp32` arayın → **esp32 by Espressif Systems** → **Install**. (Firmware hem 2.x hem 3.x sürümüyle derlenir.)
4. **USB sürücüsü:** ESP32 kartındaki USB yongasına bakın.
   - `CP2102` yazıyorsa: Silicon Labs CP210x sürücüsü
   - `CH340` / `CH9102` yazıyorsa: WCH CH34x sürücüsü
   - macOS'ta çoğu zaman sürücü gerekmez; port görünmüyorsa kurun.
5. **Veri taşıyan** bir micro-USB kablo kullanın. Sadece şarj eden kablolar portu göstermez (en sık yaşanan sorun budur).

### 1.2 Yükleme

1. Repodan `firmware/handpilot_esp32/handpilot_esp32.ino` dosyasını Arduino IDE ile açın (`config.h` yan sekmede açılır).
2. `config.h` içinde `AP_PASSWORD` değerini ekibe özel bir şifreyle değiştirin (en az 8 karakter).
3. **Tools → Board → esp32 → ESP32 Dev Module**
4. **Tools → Port** →
   - macOS: `/dev/cu.usbserial-…` ya da `/dev/cu.SLAB_USBtoUART` / `/dev/cu.wchusbserial…`
   - Windows: `COM3`, `COM4`…
5. **Upload** (sağ ok) düğmesine basın.
6. Konsolda `Connecting........` yazıp takılırsa: karttaki **BOOT** düğmesini basılı tutun, `Writing… %` yazısı görünce bırakın.
7. **Tools → Serial Monitor**, sağ altta **115200 baud** seçin, karttaki **EN/RST** düğmesine basın. Şunu görmelisiniz:
   ```
   AP started 192.168.4.1  SSID=HandPilot-Car
   ```

> **İlk yüklemede motor pilini bağlamayın.** Sadece USB ile yükleyin ve test edin. Motor gücü 2. adımda bağlanır.

### 1.3 Sık hatalar

| Belirti | Çözüm |
|---|---|
| Port listesinde kart yok | Başka (veri) kablo, sürücü kurulumu, başka USB girişi |
| `Failed to connect to ESP32: Timed out` | Yüklerken BOOT'a basılı tutun |
| `ledcSetup was not declared` | Eski bir dosya; repodaki güncel `.ino` her iki çekirdekle derlenir |
| Seri monitörde anlamsız karakterler | Baud 115200 değil |
| Kablolar takılıyken kart açılmıyor | GPIO12'ye bir şey bağlı olmamalı (PWMB = GPIO13) |

---

## 2. Aracı test etme (el olmadan)

Motor pili, sigorta ve switch bağlı, araç **tekerleri havada** (bir kutunun üstünde).

### 2.1 Telefondan (en kolay, laptop gerekmez)

1. Telefonu **HandPilot-Car** WiFi'ına bağlayın.
2. Tarayıcıda `http://192.168.4.1/kumanda` açın.
3. Düğmeler: **İLERİ / GERİ / SOL / SAĞ** (yerinde dönüş), köşeler kavis, ortada **DUR**. **Basılı tuttuğun sürece** gider, bırakınca durur. Altta hız ayarı.

> Ağa aynı anda **tek cihaz** bağlanabilir. Laptopla sürmeden önce telefonun WiFi'ını kapatın.

### 2.2 Yön ayarı (bir kez): `tools/arac_testi.py`

```bash
python tools/arac_testi.py
```

Program her adımda tekerlerin ne yapması **gerektiğini** yazar (ileri, geri, yerinde sol, yerinde sağ, iki kavis), ENTER'a basınca 1,5 sn uygular.

| Gördüğün | Çözüm (`firmware/handpilot_esp32/config.h`, sonra yeniden yükle) |
|---|---|
| İLERİ'de bir teker geri dönüyor | O tekerin `INVERT_LEFT` / `INVERT_RIGHT` değerini `1` yap |
| YERİNDE SOL'da araç sağa dönüyor | Sol ve sağ motor yer değiştirmiş: TB6612'de A ve B motor kablolarını değiştir |
| Teker hiç dönmüyor / vınlıyor | `MIN_PWM`'i artır; STBY, VM, sigorta ve pil voltajını (≥ 4,4 V yükte) kontrol et |
| Yerinde dönüş çok hızlı | `PIVOT_SCALE`'i 0.8'e düşür |

**Ölü bölge:** `python tools/arac_testi.py --hiz 80`, `--hiz 100`… Tekerlerin güvenle döndüğü en küçük değeri `MIN_PWM` yapın.

### 2.3 Tarayıcıdan tek komut

`http://192.168.4.1/cmd?d=1&s=180&t=N&seq=1` → ileri, **1 sn sonra durur** (watchdog, normal). Sonraki denemelerde `seq`'i artırın. `d=-1` geri, `d=0&t=L` yerinde sola dönüş.

### 2.4 Klavyeyle sürüş

```bash
python main.py --keyboard
```

`W` ileri (mandallı) · `S` basılı = geri · `A` / `D` basılı: giderken kavis, dururken yerinde dönüş · `SPACE` dur · `Q` çıkış. Kabul kriteri K3: 20 komutun 20'si doğru.

---

## 3. Elle sürüş

### 3.1 Kurulum (bir kez)

```bash
git clone https://github.com/furkhangul/handpilot-car
cd handpilot-car
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                              # 28 test yeşil olmalı
```

TensorFlow **gerekmez**. Dört model `models/runtime/` içinde TFLite olarak hazırdır.

### 3.2 Önce araçsız tanıma testi

```bash
python main.py --no-car
```

Ekranın üstünde 4 modelin oyu (`sinem:gaz reyyan:gaz sibel:gaz hazal:gaz`), altta ortak olasılık çubukları görünür. Araca hiçbir şey gönderilmez. Her hareketi 10'ar kez deneyin (K2: her hareket en az 9/10, diğer hareketlerde yanlış gaz 0).

### 3.3 Sürüş

1. Araç açık, laptop **HandPilot-Car** ağında.
2. `python main.py`
3. Sağ üstte `WiFi OK xx ms` görünmeli.
4. Önce ✋ açık el (DURUYOR), sonra ✊ yumruk → araç ileri kalkar. ⬅️ / ➡️ (başparmak) ile kavis alır, ✋ ile durur. Dururken 👎 geri, ⬅️ / ➡️ yerinde dönüş.
5. `SPACE` acil durdurur, `Q` çıkar (çıkarken araca `/stop` gider).

Her sürüş `logs/drive_<tarih>.csv` dosyasına kaydedilir (Git'e girmez).

---

## 4. Modeller nasıl birleştiriliyor?

| Model | Girdi | Kare başına | Ağırlık |
|---|---|---|---|
| Sinem | 21 nokta → 76 özellik, MLP | ~0,1 ms | 1,0 |
| Reyyan | 21 nokta → 63 özellik, MLP | ~0,02 ms | 1,0 |
| Sibel | El kırpması 160×160, MobileNetV3Small | ~7 ms | 1,0 |
| Hazal | El kırpması 192×192, MobileNetV3Small | ~10 ms | 0,5 |

MediaPipe her karede **bir kez** çalışır; aynı el noktaları iki MLP'ye, aynı el kırpması iki CNN'e gider. Karar kuralı (`handpilot/gesture.py`):

- **Fren:** 4 modelin ortalaması ≥ 0,60 **ya da** en az 2 model fren diyorsa. Fren her zaman kazanır.
- **Gaz:** en az 3 model gaz diyor, onların ortalama güveni ≥ 0,85, **ve** kural: en fazla 1 açık parmak, başparmak kapalı.
- **Yön:** en az 3 model aynı yön, güvenleri ≥ 0,75, **ve** kural: 4 parmak kapalı, başparmak açık, yataydan ≤ 35°, o tarafı gösteriyor.
- **Geri:** modellerde sınıfı yok; 4 parmak kapalı, başparmak açık ve aşağıyı gösteriyor (yataydan ≥ 55°).
- Aksi halde `diger`: önceki komut korunur, 1 sn sürerse araç durur.

Bir modeli çıkarmak: `python main.py --models sinem,reyyan,sibel`. Modeller değişirse:

```bash
pip install -r requirements-export.txt
python tools/export_models.py
```
