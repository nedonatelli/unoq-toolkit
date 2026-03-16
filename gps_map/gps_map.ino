// GPS Map Display — shows Esri satellite imagery on TFT centered on GPS position
// GPS TX -> D0 (RX), TFT on HW SPI (D13/D11/D10/D9/D8/D7)
// u-blox M10 at 115200 baud
//
// Bridge RPC methods:
//   get_gps  -> returns "lat,lon" in decimal degrees, or "nofix"
//   set_row  -> receives "row,col,base64data" (native 240x135 pixels)
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
uint8_t b64dec[480];  // base64 decode buffer (max 480 bytes for 240 pixels)

// Base64 decode table: maps ASCII char to 6-bit value
static const int8_t b64val[128] = {
  -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
  -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
  -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,62,-1,-1,-1,63,
  52,53,54,55,56,57,58,59,60,61,-1,-1,-1, 0,-1,-1,
  -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,
  15,16,17,18,19,20,21,22,23,24,25,-1,-1,-1,-1,-1,
  -1,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,
  41,42,43,44,45,46,47,48,49,50,51,-1,-1,-1,-1,-1
};

int base64_decode(const char *src, int srcLen, uint8_t *dst) {
  int j = 0;
  for (int i = 0; i + 3 < srcLen; i += 4) {
    uint32_t n = ((uint32_t)b64val[(uint8_t)src[i]] << 18) |
                 ((uint32_t)b64val[(uint8_t)src[i+1]] << 12) |
                 ((uint32_t)b64val[(uint8_t)src[i+2]] << 6) |
                 (uint32_t)b64val[(uint8_t)src[i+3]];
    dst[j++] = (n >> 16) & 0xFF;
    if (src[i+2] != '=') dst[j++] = (n >> 8) & 0xFF;
    if (src[i+3] != '=') dst[j++] = n & 0xFF;
  }
  return j;
}

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

String set_row(String param) {
  // Format: "row,col,base64data"
  // row = y (0-134), col = x (0-239), native 240x135 pixels
  // base64 encodes RGB565 pixels (2 bytes each, big-endian)
  int comma1 = param.indexOf(',');
  if (comma1 < 0) return String("err");
  int comma2 = param.indexOf(',', comma1 + 1);
  if (comma2 < 0) return String("err");

  int row = param.substring(0, comma1).toInt();
  int col = param.substring(comma1 + 1, comma2).toInt();
  if (row < 0 || row > 134 || col < 0 || col > 239) return String("err");

  // Decode base64 into raw bytes
  int b64Start = comma2 + 1;
  int b64Len = param.length() - b64Start;
  int rawBytes = base64_decode(param.c_str() + b64Start, b64Len, b64dec);
  int pixels = rawBytes / 2;  // 2 bytes per RGB565 pixel
  if (pixels > 240 - col) pixels = 240 - col;

  for (int p = 0; p < pixels; p++) {
    rowBuf[p] = ((uint16_t)b64dec[p * 2] << 8) | b64dec[p * 2 + 1];
  }

  tft->draw16bitRGBBitmap(col, row, rowBuf, pixels, 1);
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
