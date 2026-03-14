// GPS Satellite Display on TFT (ST7789 135x240)
// Shows satellite sky plot, signal bars, coordinates, and time
// GPS TX -> D0 (RX), TFT on HW SPI (D13/D11/D10/D9/D8/D7)
// u-blox M10 at 115200 baud
//
// Uses full-screen canvas (240x135) for flicker-free rendering
#include <Arduino_GFX_Library.h>
#include <SPI.h>
#include <math.h>

#define BLACK   0x0000
#define WHITE   0xFFFF
#define GREEN   0x07E0
#define CYAN    0x07FF
#define YELLOW  0xFFE0
#define RED     0xF800
#define GRAY    0x8410

#define TFT_CS   10
#define TFT_DC    9
#define TFT_RST   8
#define TFT_BL    7

Arduino_DataBus *bus = new Arduino_HWSPI(TFT_DC, TFT_CS, &SPI, 60000000);
Arduino_ST7789 *tft = new Arduino_ST7789(bus, TFT_RST, 0, true, 135, 240, 52, 40, 53, 40);
Arduino_Canvas *canvas = new Arduino_Canvas(240, 135, tft, 0, 0);

// NMEA parser
char lineBuf[128];
int linePos = 0;

// GPS data
int fixQuality = 0;
int satsInUse = 0;
int satsInView = 0;
char timeStr[12] = "--:--:--";
char latStr[16] = "---.----";
char latDir = '-';
char lonStr[16] = "---.----";
char lonDir = '-';
char altStr[12] = "----";
float hdop = 99.9;

// Individual satellite info from GSV (up to 32 sats)
#define MAX_SATS 32
struct SatInfo {
  int prn;
  int elev;
  int azim;
  int snr;
  bool active;
} sats[MAX_SATS];
int satCount = 0;

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
  if (getField(line, 1, val, sizeof(val)) >= 6) {
    timeStr[0] = val[0]; timeStr[1] = val[1]; timeStr[2] = ':';
    timeStr[3] = val[2]; timeStr[4] = val[3]; timeStr[5] = ':';
    timeStr[6] = val[4]; timeStr[7] = val[5]; timeStr[8] = '\0';
  }
  if (getField(line, 2, val, sizeof(val)) > 0) {
    strncpy(latStr, val, sizeof(latStr) - 1);
    latStr[sizeof(latStr) - 1] = '\0';
  }
  if (getField(line, 3, val, sizeof(val)) > 0) latDir = val[0];
  if (getField(line, 4, val, sizeof(val)) > 0) {
    strncpy(lonStr, val, sizeof(lonStr) - 1);
    lonStr[sizeof(lonStr) - 1] = '\0';
  }
  if (getField(line, 5, val, sizeof(val)) > 0) lonDir = val[0];
  if (getField(line, 6, val, sizeof(val)) > 0) fixQuality = atoi(val);
  else fixQuality = 0;
  if (getField(line, 7, val, sizeof(val)) > 0) satsInUse = atoi(val);
  if (getField(line, 8, val, sizeof(val)) > 0) hdop = atof(val);
  if (getField(line, 9, val, sizeof(val)) > 0) {
    strncpy(altStr, val, sizeof(altStr) - 1);
    altStr[sizeof(altStr) - 1] = '\0';
  }
}

void parseGSV(const char *line) {
  char val[16];
  if (getField(line, 3, val, sizeof(val)) > 0)
    satsInView = atoi(val);

  for (int s = 0; s < 4; s++) {
    int base = 4 + s * 4;
    char prnStr[8];
    if (getField(line, base, prnStr, sizeof(prnStr)) == 0) break;
    int prn = atoi(prnStr);
    if (prn == 0) continue;

    int idx = -1;
    for (int i = 0; i < satCount; i++) {
      if (sats[i].prn == prn) { idx = i; break; }
    }
    if (idx < 0 && satCount < MAX_SATS) idx = satCount++;
    if (idx < 0) continue;

    sats[idx].prn = prn;
    sats[idx].active = true;
    if (getField(line, base + 1, val, sizeof(val)) > 0) sats[idx].elev = atoi(val);
    if (getField(line, base + 2, val, sizeof(val)) > 0) sats[idx].azim = atoi(val);
    if (getField(line, base + 3, val, sizeof(val)) > 0) sats[idx].snr = atoi(val);
    else sats[idx].snr = 0;
  }
}

void processLine(const char *line) {
  if (strstr(line, "GGA")) parseGGA(line);
  if (strstr(line, "GSV")) parseGSV(line);
}

uint16_t snrColor(int snr) {
  if (snr == 0) return GRAY;
  if (snr < 20) return RED;
  if (snr < 35) return YELLOW;
  return GREEN;
}

void drawSkyPlot(Arduino_Canvas *c, int cx, int cy, int radius) {
  c->drawCircle(cx, cy, radius, GRAY);
  c->drawCircle(cx, cy, radius * 2 / 3, GRAY);
  c->drawCircle(cx, cy, radius / 3, GRAY);
  c->drawLine(cx - radius, cy, cx + radius, cy, GRAY);
  c->drawLine(cx, cy - radius, cx, cy + radius, GRAY);

  c->setTextSize(1);
  c->setTextColor(WHITE);
  c->setCursor(cx - 2, cy - radius - 9); c->print("N");
  c->setCursor(cx - 2, cy + radius + 2); c->print("S");
  c->setCursor(cx + radius + 3, cy - 3); c->print("E");
  c->setCursor(cx - radius - 8, cy - 3); c->print("W");

  for (int i = 0; i < satCount; i++) {
    if (!sats[i].active) continue;
    float r = (float)(90 - sats[i].elev) / 90.0 * radius;
    float az = sats[i].azim * 3.14159 / 180.0;
    int sx = cx + (int)(r * sin(az));
    int sy = cy - (int)(r * cos(az));

    c->fillCircle(sx, sy, 3, snrColor(sats[i].snr));
    c->setTextColor(WHITE);
    c->setTextSize(1);
    c->setCursor(sx + 4, sy - 3);
    c->print(sats[i].prn);
  }
}

void drawSignalBars(Arduino_Canvas *c, int x, int y, int w, int h) {
  int barW = max(1, (w - 2) / max(1, satCount));
  int gap = 1;
  if (barW > 3) barW -= gap; else gap = 0;

  for (int i = 0; i < satCount && i * (barW + gap) < w; i++) {
    int barH = map(sats[i].snr, 0, 50, 0, h);
    barH = constrain(barH, 0, h);
    int bx = x + i * (barW + gap);
    if (barH > 0)
      c->fillRect(bx, y + h - barH, barW, barH, snrColor(sats[i].snr));
  }
}

void drawInfoPanel(Arduino_Canvas *c, int x, int y) {
  c->setTextSize(1);

  c->setTextColor(WHITE); c->setCursor(x, y); c->print("UTC ");
  c->setTextColor(CYAN); c->print(timeStr);

  c->setCursor(x, y + 12); c->setTextColor(WHITE); c->print("FIX ");
  if (fixQuality > 0) { c->setTextColor(GREEN); c->print("3D"); }
  else { c->setTextColor(RED); c->print("NO"); }

  c->setCursor(x, y + 24); c->setTextColor(WHITE); c->print("SAT ");
  c->setTextColor(GREEN); c->print(satsInUse);
  c->setTextColor(WHITE); c->print("/");
  c->setTextColor(YELLOW); c->print(satsInView);

  c->setCursor(x, y + 36); c->setTextColor(WHITE); c->print("HDP ");
  if (hdop < 2.0) c->setTextColor(GREEN);
  else if (hdop < 5.0) c->setTextColor(YELLOW);
  else c->setTextColor(RED);
  c->print(hdop, 1);

  if (fixQuality > 0) {
    c->setCursor(x, y + 52); c->setTextColor(WHITE); c->print("LAT ");
    c->setTextColor(CYAN); c->print(latStr); c->print(latDir);

    c->setCursor(x, y + 64); c->setTextColor(WHITE); c->print("LON ");
    c->setTextColor(CYAN); c->print(lonStr); c->print(lonDir);

    c->setCursor(x, y + 76); c->setTextColor(WHITE); c->print("ALT ");
    c->setTextColor(CYAN); c->print(altStr); c->print("m");
  }
}

unsigned long lastDraw = 0;

void setup() {
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);

  Serial.begin(115200);

  tft->begin();
  delay(100);
  tft->setRotation(1);
  tft->fillScreen(BLACK);

  canvas->begin();
}

void loop() {
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

  if (millis() - lastDraw >= 1000) {
    lastDraw = millis();

    canvas->fillScreen(BLACK);

    // Title
    canvas->setTextSize(1);
    canvas->setTextColor(CYAN);
    canvas->setCursor(55, 2);
    canvas->print("GPS SATELLITE TRACKER");

    // Sky plot
    drawSkyPlot(canvas, 58, 72, 46);

    // Info panel
    drawInfoPanel(canvas, 125, 16);

    // Signal bars
    drawSignalBars(canvas, 125, 100, 110, 30);

    canvas->flush();
  }
}
