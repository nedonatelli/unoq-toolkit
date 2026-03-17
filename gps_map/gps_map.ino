// GPS Map Display — shows Esri satellite imagery on TFT centered on GPS position
// GPS TX -> D0 (RX), TFT on HW SPI (D13/D11/D10/D9/D8/D7)
// u-blox M10 at 115200 baud
//
// Bridge RPC methods:
//   get_gps  -> returns "lat,lon" in decimal degrees, or "nofix"
//   set_row  -> receives (int row, bin raw_rgb565) — full 240px row
//   clear    -> fills TFT black
//
// Run board/gps_map.py on the Linux side to fetch and push map tiles.
#include <Arduino_GFX_Library.h>
#include <Arduino_RouterBridge.h>
#include <SPI.h>

#define BLACK   0x0000
#define WHITE   0xFFFF
#define GREEN   0x07E0
#define CYAN    0x07FF
#define RED     0xF800

#define TFT_CS   10
#define TFT_DC    9
#define TFT_RST   8
#define TFT_BL    7

Arduino_DataBus *bus = new Arduino_HWSPI(TFT_DC, TFT_CS, &SPI, 60000000);
Arduino_ST7789 *tft = new Arduino_ST7789(bus, TFT_RST, 0, true, 135, 240, 52, 40, 53, 40);

// GPS state
char lineBuf[128];
int linePos = 0;
float gpsLat = 0, gpsLon = 0;
bool hasFix = false;
char latRaw[16] = "", lonRaw[16] = "";
char latDirRaw = 'N', lonDirRaw = 'W';

// Pixel buffer for native 240x135 display
uint16_t rowBuf[240];

float nmeaToDecimal(const char* nmea, char dir) {
  float val = atof(nmea);
  int degrees = (int)(val / 100);
  float minutes = val - degrees * 100;
  float decimal = degrees + minutes / 60.0;
  if (dir == 'S' || dir == 'W') decimal = -decimal;
  return decimal;
}

int getField(const char *s, int fieldNum, char *out, int maxLen) {
  int field = 0, i = 0, start = 0;
  while (s[i]) {
    if (s[i] == ',' || s[i] == '*') {
      if (field == fieldNum) {
        int len = i - start;
        if (len > maxLen - 1) len = maxLen - 1;
        memcpy(out, s + start, len);
        out[len] = '\0';
        return len;
      }
      field++;
      start = i + 1;
    }
    i++;
  }
  out[0] = '\0';
  return 0;
}

void parseGGA(const char *line) {
  char val[20];

  // Latitude (field 2) + N/S (field 3)
  if (getField(line, 2, val, sizeof(val)) > 0) {
    strncpy(latRaw, val, sizeof(latRaw) - 1);
    latRaw[sizeof(latRaw) - 1] = '\0';
  }
  if (getField(line, 3, val, sizeof(val)) > 0) latDirRaw = val[0];

  // Longitude (field 4) + E/W (field 5)
  if (getField(line, 4, val, sizeof(val)) > 0) {
    strncpy(lonRaw, val, sizeof(lonRaw) - 1);
    lonRaw[sizeof(lonRaw) - 1] = '\0';
  }
  if (getField(line, 5, val, sizeof(val)) > 0) lonDirRaw = val[0];

  // Fix quality (field 6)
  if (getField(line, 6, val, sizeof(val)) > 0) {
    int fix = atoi(val);
    if (fix > 0 && strlen(latRaw) > 0 && strlen(lonRaw) > 0) {
      gpsLat = nmeaToDecimal(latRaw, latDirRaw);
      gpsLon = nmeaToDecimal(lonRaw, lonDirRaw);
      hasFix = true;
    } else {
      hasFix = false;
    }
  }
}

void processLine(const char *line) {
  if (strstr(line, "GGA")) parseGGA(line);
}

// --- Bridge RPC handlers ---

int rpcCallCount = 0;

String get_gps(String param) {
  rpcCallCount++;
  if (!hasFix) return String("nofix");
  char buf[40];
  snprintf(buf, sizeof(buf), "%.7f,%.7f", gpsLat, gpsLon);
  return String(buf);
}

String set_row(int row, MsgPack::bin_t<uint8_t> data) {
  // Raw RGB565 pixels (2 bytes each, big-endian), drawn at row y
  if (row < 0 || row > 134) return String("err");
  int pixels = data.size() / 2;
  if (pixels > 240) pixels = 240;

  for (int p = 0; p < pixels; p++) {
    rowBuf[p] = ((uint16_t)data[p * 2] << 8) | data[p * 2 + 1];
  }

  tft->draw16bitRGBBitmap(0, row, rowBuf, pixels, 1);
  return String("ok");
}

String clear_screen(String param) {
  tft->fillScreen(BLACK);
  return String("ok");
}

void setup() {
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);

  Serial.begin(115200);  // GPS

  tft->begin();
  delay(100);
  tft->setRotation(1);
  tft->fillScreen(BLACK);

  // Show waiting message
  tft->setTextSize(1);
  tft->setTextColor(CYAN);
  tft->setCursor(60, 55);
  tft->print("GPS MAP DISPLAY");
  tft->setTextColor(WHITE);
  tft->setCursor(45, 70);
  tft->print("Waiting for GPS fix...");

  // Register Bridge RPC methods — retry until router is ready
  // Use 921600 baud for faster image transfer (must match router --serial-baudrate)
  while (!Bridge.begin()) {
    tft->setCursor(5, 85);
    tft->setTextColor(0xFFE0);
    tft->print("Bridge: connecting...");
    delay(1000);
  }
  tft->fillRect(0, 85, 240, 10, BLACK);
  tft->setCursor(5, 85);
  tft->setTextColor(GREEN);
  tft->print("Bridge: connected");

  bool p1 = Bridge.provide("get_gps", get_gps);
  bool p2 = Bridge.provide("set_row", set_row);
  bool p3 = Bridge.provide("clear", clear_screen);

  tft->fillRect(0, 85, 240, 10, BLACK);
  tft->setCursor(5, 85);
  tft->setTextColor(GREEN);
  tft->print("RPC: ");
  tft->print(p1 ? "gps:OK " : "gps:FAIL ");
  tft->print(p2 ? "row:OK " : "row:FAIL ");
  tft->print(p3 ? "clr:OK" : "clr:FAIL");
}

bool mapReceived = false;

void loop() {
  // Read GPS NMEA sentences
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (linePos > 0) {
        lineBuf[linePos] = '\0';
        processLine(lineBuf);
        linePos = 0;
      }
    } else if (linePos < 127) {
      lineBuf[linePos++] = c;
    }
  }
}
