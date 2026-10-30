// HandPilot-Car · ESP32 + TB6612FNG firmware (README §11, §12)
//
// Açılışta motorlar KAPALI, sonra WiFi erişim noktası açılır (192.168.4.1).
//   GET /                          -> "HandPilot-Car OK"
//   GET /kumanda                   -> telefondan basılı tutmalı test kumandası (laptopsuz)
//   GET /cmd?d=1&s=180&t=N&seq=1   -> sür
//        d:  1 ileri · -1 geri · 0 ilerleme yok (s > 0 ve t = L/R ise YERİNDE dönüş)
//        s:  0-255 hız   t: N düz · L sol · R sağ   seq: artan sayı
//   GET /stop                      -> anında dur
//   GET /status                    -> çalışma süresi, son komut yaşı, seq, hareket, pil voltajı
// 1 sn komut gelmezse kendi durur (watchdog). Seri port: 115200 baud.

#include <WiFi.h>
#include <WebServer.h>
#include "config.h"

WebServer server(80);
unsigned long lastCmdMs = 0;
long lastSeq = 0;
bool moving = false;

// ---------- PWM: ESP32 Arduino çekirdeği 2.x ve 3.x ikisiyle de derlenir ----------
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
void pwmBegin() {
  ledcAttach(PIN_PWMA, PWM_FREQ, PWM_BITS);
  ledcAttach(PIN_PWMB, PWM_FREQ, PWM_BITS);
}
void pwmWrite(int pin, int duty) { ledcWrite(pin, duty); }
#else
void pwmBegin() {
  ledcSetup(0, PWM_FREQ, PWM_BITS); ledcAttachPin(PIN_PWMA, 0);
  ledcSetup(1, PWM_FREQ, PWM_BITS); ledcAttachPin(PIN_PWMB, 1);
}
void pwmWrite(int pin, int duty) { ledcWrite(pin == PIN_PWMA ? 0 : 1, duty); }
#endif

// duty: -255..255 (eksi = geri)
void setMotor(int pinPwm, int in1, int in2, int duty, bool invert) {
  if (invert) duty = -duty;
  if (duty == 0) {  // Serbest bırak (iki giriş LOW)
    digitalWrite(in1, LOW); digitalWrite(in2, LOW);
  } else {
    digitalWrite(in1, duty > 0 ? HIGH : LOW); digitalWrite(in2, duty > 0 ? LOW : HIGH);
  }
  pwmWrite(pinPwm, abs(duty));
}

void setWheels(int left, int right) {
  digitalWrite(PIN_STBY, (left || right) ? HIGH : LOW);
  setMotor(PIN_PWMA, PIN_AIN1, PIN_AIN2, left, INVERT_LEFT);
  setMotor(PIN_PWMB, PIN_BIN1, PIN_BIN2, right, INVERT_RIGHT);
}

void stopMotors() {
  setWheels(0, 0);
  if (moving) Serial.println("STOP");
  moving = false;
}

// Komutu iki tekerin hızına çevirir
void drive(int d, int speed, char turn) {
  speed = constrain(speed, 0, 255);
  if (speed == 0 || (d == 0 && turn == 'N')) { stopMotors(); return; }
  if (speed < MIN_PWM) speed = MIN_PWM;
  int left = speed, right = speed;
  if (d == 0) {                                   // Yerinde dönüş: tekerler zıt yönde
    int p = max((int)(speed * PIVOT_SCALE), MIN_PWM);
    left  = (turn == 'L') ? -p : p;
    right = (turn == 'L') ? p : -p;
  } else {                                        // İleri / geri, gerekirse kavis
    int inner = max((int)(speed * TURN_INNER), turn == 'N' ? 0 : MIN_PWM / 2);
    if (turn == 'L') left = inner;                // Sola dönerken sol (iç) teker yavaş
    if (turn == 'R') right = inner;
    left *= d; right *= d;
  }
  setWheels(left, right);
  moving = true;
}

float readVbat() {
  return analogReadMilliVolts(PIN_VBAT) / 1000.0f * VBAT_DIVIDER;
}

void badRequest(const char *why) {
  stopMotors();  // Geçersiz komut -> dur
  server.send(400, "application/json", String("{\"ok\":0,\"err\":\"") + why + "\"}");
}

void handleCmd() {
  if (!server.hasArg("d") || !server.hasArg("s") || !server.hasArg("t") || !server.hasArg("seq")) {
    badRequest("eksik parametre"); return;
  }
  int d = server.arg("d").toInt();
  int s = server.arg("s").toInt();
  String t = server.arg("t");
  long seq = server.arg("seq").toInt();
  if (d < -1 || d > 1 || s < 0 || s > 255 || !(t == "N" || t == "L" || t == "R")) {
    badRequest("gecersiz deger"); return;
  }
  if (seq == 1) lastSeq = 0;  // İstemci yeniden başladı
  if (seq <= lastSeq) {       // Geç gelen eski paket aracı yeniden kaldıramaz
    server.send(200, "application/json", String("{\"ok\":0,\"seq\":") + lastSeq + ",\"err\":\"eski seq\"}");
    return;
  }
  lastSeq = seq;
  lastCmdMs = millis();
  drive(d, s, t[0]);
  Serial.printf("cmd seq=%ld d=%d s=%d t=%s\n", seq, d, s, t.c_str());
  server.send(200, "application/json", String("{\"ok\":1,\"seq\":") + seq + "}");
}

void handleStop() {
  stopMotors();
  lastCmdMs = millis();
  server.send(200, "application/json", "{\"ok\":1}");
}

void handleStatus() {
  String json = String("{\"uptime_ms\":") + millis() +
                ",\"last_cmd_age_ms\":" + (millis() - lastCmdMs) +
                ",\"seq\":" + lastSeq +
                ",\"moving\":" + (moving ? 1 : 0) +
                ",\"vbat\":" + String(readVbat(), 2) + "}";
  server.send(200, "application/json", json);
}

// Basılı tuttukça 200 ms'de bir /cmd yollar, bırakınca /stop. Laptop gerekmez.
const char KUMANDA_HTML[] PROGMEM = R"HTML(<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>HandPilot-Car Kumanda</title><style>
body{font-family:sans-serif;background:#111;color:#eee;margin:0;padding:16px;text-align:center;user-select:none}
.g{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;max-width:420px;margin:16px auto}
button{font-size:20px;padding:26px 0;border:0;border-radius:12px;background:#2a2a2a;color:#eee;touch-action:none}
button:active,button.on{background:#2f7d32}#stop{background:#b71c1c}
input{width:80%}</style></head><body>
<h3>HandPilot-Car</h3><div id="st">hazir</div>
<div class="g">
<button data-d="1" data-t="L">&#8598;</button><button data-d="1" data-t="N">ILERI</button><button data-d="1" data-t="R">&#8599;</button>
<button data-d="0" data-t="L">SOL</button><button id="stop">DUR</button><button data-d="0" data-t="R">SAG</button>
<button data-d="-1" data-t="L">&#8601;</button><button data-d="-1" data-t="N">GERI</button><button data-d="-1" data-t="R">&#8600;</button>
</div>Hiz <span id="sv">180</span><br><input id="sp" type="range" min="80" max="255" value="180">
<p>Basili tuttugun surece gider, birakinca durur.</p>
<script>
let seq=1,timer=null,cur=null;const st=document.getElementById('st'),sp=document.getElementById('sp');
sp.oninput=()=>document.getElementById('sv').textContent=sp.value;
function send(){fetch('/cmd?d='+cur.dataset.d+'&s='+sp.value+'&t='+cur.dataset.t+'&seq='+(seq++)).then(r=>r.json()).then(j=>st.textContent=j.ok?'gidiyor':'reddedildi').catch(()=>st.textContent='baglanti yok');}
function stop(){if(timer){clearInterval(timer);timer=null}if(cur){cur.classList.remove('on');cur=null}fetch('/stop').then(()=>st.textContent='durdu').catch(()=>{});}
document.querySelectorAll('button[data-d]').forEach(b=>{
b.addEventListener('pointerdown',e=>{e.preventDefault();stop();cur=b;b.classList.add('on');send();timer=setInterval(send,200);});
['pointerup','pointerleave','pointercancel'].forEach(ev=>b.addEventListener(ev,stop));});
document.getElementById('stop').addEventListener('pointerdown',stop);
document.addEventListener('visibilitychange',stop);
</script></body></html>)HTML";

void setup() {
  // 1) Önce motorlar kesin kapalı (WiFi'dan ÖNCE)
  pinMode(PIN_STBY, OUTPUT); digitalWrite(PIN_STBY, LOW);
  int outs[] = {PIN_AIN1, PIN_AIN2, PIN_BIN1, PIN_BIN2, PIN_PWMA, PIN_PWMB};
  for (int p : outs) { pinMode(p, OUTPUT); digitalWrite(p, LOW); }
  pwmBegin();
  stopMotors();

  Serial.begin(115200);
  delay(200);

  // 2) WiFi erişim noktası
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD, 1, 0, 1);  // kanal 1, gizli değil, en fazla 1 istemci
  WiFi.setSleep(false);                         // Gecikmeyi düşürür
  Serial.printf("AP started %s  SSID=%s\n", WiFi.softAPIP().toString().c_str(), AP_SSID);

  server.on("/", []() { server.send(200, "text/plain", "HandPilot-Car OK"); });
  server.on("/kumanda", []() { server.send_P(200, "text/html", KUMANDA_HTML); });
  server.on("/cmd", handleCmd);
  server.on("/stop", handleStop);
  server.on("/status", handleStatus);
  server.onNotFound([]() { server.send(404, "text/plain", "yok"); });
  server.begin();
}

void loop() {
  server.handleClient();
  if (moving && millis() - lastCmdMs > WATCHDOG_MS) {
    Serial.println("WATCHDOG: 1 sn komut yok");
    stopMotors();
  }
}
