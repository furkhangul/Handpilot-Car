# HandPilot Car — VS Code ile çalıştırma

Bu paket bağımlılıksız, statik bir web arayüzüdür. `npm install` veya ek bir derleme işlemi gerekmez.

## VS Code ile çalıştırma

1. ZIP dosyasını bir klasöre çıkarın.
2. Visual Studio Code'u açın.
3. **File → Open Folder** ile çıkardığınız `HandPilotCar-Web-Arayuzu` klasörünü seçin.
4. VS Code terminalini açın: **Terminal → New Terminal**.
5. İşletim sisteminize uygun komutu çalıştırın:

### macOS / Linux

```bash
python3 -m http.server 4173
```

### Windows

```powershell
py -m http.server 4173
```

6. Tarayıcıda şu adresi açın:

```text
http://localhost:4173
```

Sunucuyu durdurmak için terminalde `Control + C` tuşlarına basın.

## Daha kısa yöntemler

- macOS'ta `baslat.command` dosyasına çift tıklayabilirsiniz.
- Windows'ta `baslat.bat` dosyasına çift tıklayabilirsiniz.
- VS Code'da **Terminal → Run Task → HandPilot web sunucusunu başlat** görevini çalıştırabilirsiniz.

## Düzenlenecek temel dosyalar

- `index.html`: Sayfa içeriği ve bölümler
- `styles.css`: Tasarım, responsive düzen ve animasyonlar
- `app.js`: Kaydırma geçişleri ve araç simülasyonu
- Ana kumanda görseli tamamen `index.html` ve `styles.css` içinde kodla oluşturulur.
- Kumandanın kırılma mesafesi ve dönüş açıları `app.js` içindeki `breakProgress` bölümünden değiştirilebilir.

> Not: `index.html` dosyasını doğrudan çift tıklayarak da açabilirsiniz; ancak en doğru sonuç için yerel sunucu yöntemi önerilir.
