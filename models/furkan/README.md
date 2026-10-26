# HandPilot Model (Furkan)

Sınıflar: gaz, fren, sol, sag · Test kişileri: 1333, hzl1 (eğitimde kullanılmadı)

| Sürüm | Model | Girdi | Test doğruluğu | Macro F1 |
|---|---|---|---|---|
| **v2 (güncel)** | MLP 128-64 (`v2_landmark_mlp/`) | 21 MediaPipe el noktası → 76 özellik | **%100** | **1,0000** |
| v1 | MobileNetV3Small CNN (`v1_cnn/`) | MediaPipe el ROI, 192×192 RGB | %94,59 | 0,9440 |

## v2 — El noktası tabanlı MLP
v1'de en zayıf sınıf `sol` idi (recall %79,9). Görüntü yerine el noktalarına geçilerek bu sorun giderildi.

- Özellikler: bilek (0) orijin, 0–9 mesafesine bölme, döndürme yok → 63 koordinat + 13 geometrik özellik
  (parmak açıklık oranları, parmak ucu–bilek mesafeleri, başparmak açısı, parmak uçları ortalama mesafesi)
- Kişi ayrımı v1 ile aynı (`v1_cnn/reports/person_split.json`): 9 kişi eğitim, 4848 ve sbl1 doğrulama, 1333 ve hzl1 test
- Test (1811 görüntü): doğruluk %100, gaz↔fren karışması 0 · Doğrulama: %99,72
- Dosyalar: `landmark_mlp.keras`, `scaler.joblib`, `classes.json`, `metrics.json`, `history.json`, `train_landmark_mlp.py`

## v1 — MobileNetV3Small CNN
- Model: `v1_cnn/final_model.keras` (TensorFlow 2.21)
- Test: doğruluk %94,59, dengeli doğruluk %94,70, Macro F1 0,9440
- Eğitim yapılandırması: `v1_cnn/manifest.json` · Metrikler ve grafikler: `v1_cnn/reports/`, `v1_cnn/figures/`
