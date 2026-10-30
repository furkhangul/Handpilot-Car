// HandPilot-Car firmware ayarları (README §12, §13). Pin değişikliği: Recep onayı.
#pragma once

// ---------- WiFi erişim noktası ----------
#define AP_SSID      "HandPilot-Car"
#define AP_PASSWORD  "handpilot2026"   // En az 8 karakter. Sunumdan önce değiştirin.

// ---------- TB6612FNG pinleri ----------
#define PIN_PWMA  25   // Sol motor hızı (GPIO14 kullanılmaz: açılışta PWM verir)
#define PIN_AIN1  26
#define PIN_AIN2  27
#define PIN_PWMB  13   // Sağ motor hızı (GPIO12 kullanılmaz: strapping pini)
#define PIN_BIN1  32
#define PIN_BIN2  33
#define PIN_STBY  23   // LOW = sürücü kapalı
#define PIN_VBAT  34   // 10k/10k bölücü (takılı değilse /status vbat anlamsız olur)

// Motor ters dönüyorsa kablo değiştirmek yerine bunu 1 yapın
#define INVERT_LEFT   0
#define INVERT_RIGHT  0

// ---------- Sürüş ----------
#define PWM_FREQ     5000
#define PWM_BITS     8
#define MIN_PWM      120    // Ölü bölge: masada ölçün, motor dönmeye başladığı değer
#define TURN_INNER   0.40f  // Kavis alırken iç teker oranı
#define PIVOT_SCALE  1.0f   // Yerinde dönüşte teker hızı = s × bu (çok hızlı dönüyorsa düşürün)
#define WATCHDOG_MS  1000   // Bu kadar komut gelmezse dur
#define VBAT_DIVIDER 2.0f
