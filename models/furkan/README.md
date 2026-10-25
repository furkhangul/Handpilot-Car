# HandPilot CNN (Furkan)

Bu klasör, HandPilot projesi kapsamında eğitilen MobileNetV3Small CNN modelini ve değerlendirme sonuçlarını içerir.

- Model: `final_model.keras` (TensorFlow 2.21, giriş 192x192, MediaPipe el ROI)
- Final test doğruluğu: %94,59
- Balanced accuracy: %94,70
- Macro F1: 0,9440
- Sınıflar: fren, gaz, sag, sol
- Eğitim yapılandırması: `manifest.json`
- Ayrıntılı metrikler ve grafikler: `reports/`, `figures/`
