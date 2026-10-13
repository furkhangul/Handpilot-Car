---
name: Hata bildirimi
about: Çalışmayan, yanlış tanıyan ya da aracı beklenmedik hareket ettiren bir durum
title: "[HATA] "
labels: bug
---

## Ne oldu?

<!-- Tek cümle. Örn: "Yumruk gösterince araç bazen kalkmıyor." -->

## Ne bekleniyordu?

## Nasıl tekrarlanır?

1.
2.
3.

## Ortam

| | |
|---|---|
| Bilgisayar / işletim sistemi | |
| Python sürümü | |
| Model sürümü (`models/gesture_clf.json`) | |
| Işık / mesafe / arka plan | |
| Araç pil voltajı (varsa) | |

## Kanıt

<!-- logs/drive_*.csv satırları, ekran görüntüsü, kısa video. Yüz görünen görüntü paylaşma (KVKK, README §9.7). -->

## Güvenlik etkisi

- [ ] Araç durması gerekirken durmadı (**öncelikli**)
- [ ] Araç kendiliğinden kalktı / yanlış gaz (**öncelikli**)
- [ ] Yalnızca konfor / görünüm sorunu
