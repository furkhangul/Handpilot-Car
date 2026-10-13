# Kabul Testi Kaydı · HandPilot-Car

> Şablon. Her ölçüm 5 kez tekrarlanır, ortalama ve en kötü değer yazılır (README §15).

| | |
|---|---|
| Tarih / saat | |
| Ortam (oda, ışık) | |
| Laptop / FPS | |
| Model sürümü | |
| Pil (yüksüz / yükte) | |
| Ölçen | |

| # | Test | Hedef | 1 | 2 | 3 | 4 | 5 | Ort. | En kötü | Sonuç |
|---|---|---|---|---|---|---|---|---|---|---|
| K1 | Çevrimdışı, görülmemiş kişi (recall min) | ≥ %95, gaz↔fren 0 | | | | | | | | |
| K2 | Canlı tanıma (10'ar deneme) | ≥ 9/10, yanlış gaz 0 | | | | | | | | |
| K3 | Klavyeyle 20 komut | 20/20 | | | | | | | | |
| K4 | Fren gecikmesi | ≤ 300 ms | | | | | | | | |
| K5 | Gaz gecikmesi | ≤ 400 ms | | | | | | | | |
| K6 | El kaybında durma | ≤ 0.6 sn | | | | | | | | |
| K7 | Watchdog | ≤ 1.1 sn | | | | | | | | |
| K8 | Pist turu | 60 sn, 0 çarpma | | | | | | | | |
| K9 | Bağlantı | 10 dk, 0 kopma | | | | | | | | |
| K10 | Döngü hızı | ≥ 20 fps | | | | | | | | |
| K11 | Fren mesafesi (hız 180) | ≤ 50 cm | | | | | | | | |

**Gecikme hesabı (240 fps):** `kare farkı × 4.17 ms`

## Notlar
