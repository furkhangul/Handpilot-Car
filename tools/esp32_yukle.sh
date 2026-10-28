#!/usr/bin/env bash
# ESP32'ye firmware yükler (Arduino IDE'nin içindeki arduino-cli ile) ve seri çıktıyı gösterir.
# Kullanım:  bash tools/esp32_yukle.sh          (port otomatik bulunur)
#            bash tools/esp32_yukle.sh /dev/cu.usbserial-0001
set -euo pipefail

CLI="${ARDUINO_CLI:-/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli}"
command -v arduino-cli >/dev/null 2>&1 && [ ! -x "$CLI" ] && CLI="$(command -v arduino-cli)"
URL="https://espressif.github.io/arduino-esp32/package_esp32_index.json"
FQBN="esp32:esp32:esp32"
SKETCH="$(cd "$(dirname "$0")/.." && pwd)/firmware/handpilot_esp32"

[ -x "$CLI" ] || { echo "arduino-cli bulunamadı. Arduino IDE 2'yi /Applications'a kurun."; exit 1; }

if ! "$CLI" core list | grep -q '^esp32:esp32'; then
  echo ">> ESP32 çekirdeği kuruluyor (bir kez, birkaç dakika)..."
  "$CLI" core update-index --additional-urls "$URL"
  "$CLI" core install esp32:esp32 --additional-urls "$URL"
fi

PORT="${1:-}"
if [ -z "$PORT" ]; then
  PORT="$(ls /dev/cu.usbserial* /dev/cu.SLAB* /dev/cu.wchusbserial* /dev/cu.usbmodem* 2>/dev/null | head -1 || true)"
fi
[ -n "$PORT" ] || { echo "ESP32 portu yok. Kartı VERİ taşıyan bir USB kabloyla takın (sadece şarj kablosu olmaz)."; exit 1; }
echo ">> Port: $PORT"

echo ">> Derleniyor..."
"$CLI" compile --fqbn "$FQBN" "$SKETCH"

echo ">> Yükleniyor... ('Connecting...' takılırsa karttaki BOOT düğmesini basılı tutun)"
"$CLI" upload --fqbn "$FQBN" -p "$PORT" "$SKETCH"

echo ">> Seri çıktı (10 sn). 'AP started 192.168.4.1' görmelisiniz. Görünmezse karttaki EN'e basın."
"$CLI" monitor -p "$PORT" -c baudrate=115200 &
MON=$!; sleep 10; kill $MON 2>/dev/null || true
echo ">> Bitti. Şimdi Mac'i 'HandPilot-Car' WiFi'ına bağlayın."
