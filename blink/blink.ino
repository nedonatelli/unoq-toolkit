// Real-time WiFi Signal Strength Monitor
// Linux pushes frame data via Bridge RPC call to "wifi_frame"
#include <Arduino_LED_Matrix.h>
#include <Arduino_RouterBridge.h>

Arduino_LED_Matrix matrix;

bool ledState = false;
unsigned long lastBlink = 0;

// Called by Linux side with 4 hex uint32s as a comma-separated string
bool onWifiFrame(String frameStr) {
  uint32_t frame[4] = {0, 0, 0, 0};
  int idx = 0;
  int start = 0;
  for (int i = 0; i <= (int)frameStr.length() && idx < 4; i++) {
    if (i == (int)frameStr.length() || frameStr[i] == ',') {
      String part = frameStr.substring(start, i);
      frame[idx++] = (uint32_t)strtoul(part.c_str(), NULL, 16);
      start = i + 1;
    }
  }
  matrix.loadFrame(frame);
  return true;
}

void setup() {
  matrix.begin();
  matrix.clear();

  pinMode(LED3_G, OUTPUT);
  digitalWrite(LED3_G, HIGH);

  Bridge.begin();
  Monitor.begin();
  Bridge.provide("wifi_frame", onWifiFrame);
  Monitor.println("WiFi Signal Monitor ready");
}

void loop() {
  unsigned long now = millis();
  if (now - lastBlink >= 500) {
    lastBlink = now;
    ledState = !ledState;
    digitalWrite(LED3_G, ledState ? LOW : HIGH);
  }
  delay(10);
}
