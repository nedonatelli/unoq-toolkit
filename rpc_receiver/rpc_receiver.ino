// Receives LED matrix frames via Bridge RPC from the Linux side.
// Use with board/clock.py or board/wifi_monitor.py.
#include <Arduino_LED_Matrix.h>
#include <Arduino_RouterBridge.h>

Arduino_LED_Matrix matrix;

uint32_t currentFrame[4] = {0, 0, 0, 0};

// Parse hex frame string "XXXXXXXX,XXXXXXXX,XXXXXXXX,XXXXXXXX"
String set_frame(String frameStr) {
  int idx = 0;
  int start = 0;
  for (int i = 0; i <= (int)frameStr.length() && idx < 4; i++) {
    if (i == (int)frameStr.length() || frameStr[i] == ',') {
      String hex = frameStr.substring(start, i);
      currentFrame[idx] = strtoul(hex.c_str(), NULL, 16);
      idx++;
      start = i + 1;
    }
  }
  matrix.loadFrame(currentFrame);
  return String("ok");
}

void setup() {
  matrix.begin();
  Bridge.begin();
  Bridge.provide("set_frame", set_frame);
}

void loop() {
}
