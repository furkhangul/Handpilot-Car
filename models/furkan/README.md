# HandPilot Model (Furkan)

Sınıflar: gaz, fren, sol, sag

| Sürüm | Model | Girdi | Doğruluk | Macro F1 | Değerlendirme |
|---|---|---|---|---|---|
| **v2 (güncel)** | MLP 128-64 (`v2_landmark_mlp/`) | 21 MediaPipe el noktası → 76 özellik | **%99,51 ± 0,95** | **0,9937** | 13 katlı kişi bazlı CV |
| v1 | MobileNetV3Small CNN (`v1_cnn/`) | MediaPipe el ROI, 192×192 RGB | %94,59 | 0,9440 | test kişileri 1333, hzl1 |

## v2 — El noktası tabanlı MLP
v1'de en zayıf sınıf `sol` idi (recall %79,9). Görüntü yerine el noktalarına geçilerek bu sorun giderildi.

- Özellikler: bilek (0) orijin, 0–9 mesafesine bölme, döndürme yok → 63 koordinat + 13 geometrik özellik
  (parmak açıklık oranları, parmak ucu–bilek mesafeleri, başparmak açısı, parmak uçları ortalama mesafesi)
- **Kişi bazlı çapraz doğrulama (leave-one-person-out, 13 kat):** her katta bir kişi tamamen test için ayrılır.
  Ortalama doğruluk %99,51 ± 0,95; en düşük kat %96,66 (2703); Macro F1 0,9937; sınıf recall: gaz %99,2, fren %99,7, sol %99,0, sag %99,9.
  Fren→gaz 4, gaz→fren 0 hata (12.492 görüntüde). Ayrıntılar: `cv_metrics.json`, kod: `cv_landmark_mlp.py`
- Son model v1 ile aynı kişi ayrımıyla eğitildi (`v1_cnn/reports/person_split.json`: 9 kişi eğitim, 4848/sbl1 doğrulama, 1333/hzl1 test); bu iki test kişisindeki sonuç %100 (`metrics.json`).
  Sadece 2 kişi olduğundan genel başarı ölçüsü olarak yukarıdaki CV sonucu esas alınmalıdır.
- Dosyalar: `landmark_mlp.keras`, `scaler.joblib`, `classes.json`, `metrics.json`, `history.json`, `train_landmark_mlp.py`, `cv_landmark_mlp.py`, `cv_metrics.json`

## v1 — MobileNetV3Small CNN
- Model: `v1_cnn/final_model.keras` (TensorFlow 2.21)
- Test: doğruluk %94,59, dengeli doğruluk %94,70, Macro F1 0,9440
- Eğitim yapılandırması: `v1_cnn/manifest.json` · Metrikler ve grafikler: `v1_cnn/reports/`, `v1_cnn/figures/`

## Rapor
- `rapor/HandPilot_Model_Sonuclari.ipynb` ve `rapor/HandPilot_Model_Sonuclari.html`: tüm modellerin doğruluk tablosu ve grafikleri
