# Veri Seti Kartı · HandPilot-Car

> Şablon. `dataset/DATASET.md` olarak kopyalayıp doldurun. Her eğitimden önce yeni sürüm satırı eklenir (README §9.6-4).

| Alan | Değer |
|---|---|
| Sürüm | v1 |
| Tarih | YYYY-AA-GG |
| Toplama aracı | `veri_topla.py` / `tools/collect_dataset.py` (commit: `…`) |
| `MIRROR` | True |
| Çözünürlük | 640×480, JPEG 95 |
| Sorumlu | |

## Kişi × sınıf tablosu (temizlik sonrası)

| Kişi | gaz | fren | sol | sag | diger | Toplam | Not (ışık, oda, gün) |
|---|---:|---:|---:|---:|---:|---:|---|
| p01 | | | | | | | |
| p02 | | | | | | | |
| p03 | | | | | | | |
| p04 | | | | | | | |
| p05 | | | | | | | |
| p06 | | | | | | | |
| p07 | | | | | | | |
| p08 | | | | | | | |
| **Toplam** | | | | | | | |

## Temizlik

| Silinen kare | Sayı | Neden |
|---|---:|---|
| MediaPipe el bulamadı (`hand_detected=0`) | | otomatik |
| Yanlış hareket / yanlış etiket | | gözle |
| Bulanık / kesik el | | gözle |

## Çeşitlilik kontrolü (README §9.5)

- [ ] 8 kişinin hepsi
- [ ] En az 2 ışık
- [ ] En az 2 arka plan
- [ ] Kısa kol / uzun kol
- [ ] 2 farklı gün
- [ ] Sunum odası + sunum laptopu

## Ayrım

| Küme | Kişiler |
|---|---|
| Eğitim | |
| Doğrulama | |
| Test | |

## Sürüm geçmişi

| Sürüm | Tarih | Değişiklik |
|---|---|---|
| v1 | | İlk tam set |
