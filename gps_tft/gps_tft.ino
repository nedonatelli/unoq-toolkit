// GPS Satellite Display on TFT (ST7789 135x240)
// Shows satellite sky plot, signal bars, coordinates, and time
// GPS TX -> D0 (RX), TFT on HW SPI (D13/D11/D10/D9/D8/D7)
// u-blox M10 at 115200 baud
#include <Arduino_GFX_Library.h>
#include <SPI.h>

#define BLACK   0x0000
#define WHITE   0xFFFF
#define GREEN   0x07E0
#define CYAN    0x07FF
#define YELLOW  0xFFE0
#define RED     0xF800
#define DKGREEN 0x03E0
#define GRAY    0x8410

#define TFT_CS   10
#define TFT_DC    9
#define TFT_RST   8
#define TFT_BL    7

Arduino_DataBus *bus = new Arduino_HWSPI(TFT_DC, TFT_CS, &SPI, 60000000);
Arduino_ST7789 *tft = new Arduino_ST7789(bus, TFT_RST, 0, true, 135, 240, 52, 40, 53, 40);

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
  int elev;   // elevation 0-90 degrees
  int azim;   // azimuth 0-360 degrees
  int snr;    // signal-to-noise 0-99 dB-Hz, 0 = not tracking
  bool active;
} sats[MAX_SATS];
int satCount = 0;

// Parse comma-separated field from NMEA
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

  // Time (field 1): HHMMSS.ss
  if (getField(line, 1, val, sizeof(val)) >= 6) {
    timeStr[0] = val[0]; timeStr[1] = val[1];
    timeStr[2] = ':';
    timeStr[3] = val[2]; timeStr[4] = val[3];
    timeStr[5] = ':';
    timeStr[6] = val[4]; timeStr[7] = val[5];
    timeStr[8] = '\0';
  }

  // Latitude (field 2) + N/S (field 3)
  if (getField(line, 2, val, sizeof(val)) > 0) {
    // DDMM.MMMM -> copy as-is for display
    strncpy(latStr, val, sizeof(latStr) - 1);
    latStr[sizeof(latStr) - 1] = '\0';
  }
  if (getField(line, 3, val, sizeof(val)) > 0) latDir = val[0];

  // Longitude (field 4) + E/W (field 5)
  if (getField(line, 4, val, sizeof(val)) > 0) {
    strncpy(lonStr, val, sizeof(lonStr) - 1);
    lonStr[sizeof(lonStr) - 1] = '\0';
  }
  if (getField(line, 5, val, sizeof(val)) > 0) lonDir = val[0];

  // Fix quality (field 6)
  if (getField(line, 6, val, sizeof(val)) > 0)
    fixQuality = atoi(val);
  else
    fixQuality = 0;

  // Sats in use (field 7)
  if (getField(line, 7, val, sizeof(val)) > 0)
    satsInUse = atoi(val);

  // HDOP (field 8)
  if (getField(line, 8, val, sizeof(val)) > 0)
    hdop = atof(val);

  // Altitude (field 9)
  if (getField(line, 9, val, sizeof(val)) > 0) {
    strncpy(altStr, val, sizeof(altStr) - 1);
    altStr[sizeof(altStr) - 1] = '\0';
  }
}

void parseGSV(const char *line) {
  char val[16];

  // Field 3: total sats in view
  if (getField(line, 3, val, sizeof(val)) > 0)
    satsInView = atoi(val);

  // Parse up to 4 satellites per GSV sentence (fields 4-7, 8-11, 12-15, 16-19)
  for (int s = 0; s < 4; s++) {
    int base = 4 + s * 4;
    char prnStr[8];
    if (getField(line, base, prnStr, sizeof(prnStr)) == 0) break;

    int prn = atoi(prnStr);
    if (prn == 0) continue;

    // Find or add this satellite
    int idx = -1;
    for (int i = 0; i < satCount; i++) {
      if (sats[i].prn == prn) { idx = i; break; }
    }
    if (idx < 0 && satCount < MAX_SATS) {
      idx = satCount++;
    }
    if (idx < 0) continue;

    sats[idx].prn = prn;
    sats[idx].active = true;

    if (getField(line, base + 1, val, sizeof(val)) > 0)
      sats[idx].elev = atoi(val);
    if (getField(line, base + 2, val, sizeof(val)) > 0)
      sats[idx].azim = atoi(val);
    if (getField(line, base + 3, val, sizeof(val)) > 0)
      sats[idx].snr = atoi(val);
    else
      sats[idx].snr = 0;
  }
}

void processLine(const char *line) {
  if (strstr(line, "GGA")) parseGGA(line);
  if (strstr(line, "GSV")) parseGSV(line);
}

// Sky plot: circular view with satellites plotted by azimuth/elevation
void drawSkyPlot(int cx, int cy, int radius) {
  // Draw horizon circles
  tft->drawCircle(cx, cy, radius, GRAY);
  tft->drawCircle(cx, cy, radius * 2 / 3, GRAY);
  tft->drawCircle(cx, cy, radius / 3, GRAY);

  // Draw crosshairs
  tft->drawLine(cx - radius, cy, cx + radius, cy, GRAY);
  tft->drawLine(cx, cy - radius, cx, cy + radius, GRAY);

  // N/S/E/W labels
  tft->setTextSize(1);
  tft->setTextColor(WHITE);
  tft->setCursor(cx - 2, cy - radius - 9);
  tft->print("N");
  tft->setCursor(cx - 2, cy + radius + 2);
  tft->print("S");
  tft->setCursor(cx + radius + 3, cy - 3);
  tft->print("E");
  tft->setCursor(cx - radius - 8, cy - 3);
  tft->print("W");

  // Plot each satellite
  for (int i = 0; i < satCount; i++) {
    if (!sats[i].active) continue;

    // Convert azimuth/elevation to x/y
    // elevation 90=center, 0=edge
    float r = (float)(90 - sats[i].elev) / 90.0 * radius;
    // azimuth: 0=N(up), 90=E(right), measured clockwise
    float az = sats[i].azim * 3.14159 / 180.0;
    int sx = cx + (int)(r * sin(az));
    int sy = cy - (int)(r * cos(az));

    // Color by signal strength
    uint16_t color;
    if (sats[i].snr == 0) color = GRAY;
    else if (sats[i].snr < 20) color = RED;
    else if (sats[i].snr < 35) color = YELLOW;
    else color = GREEN;

    tft->fillCircle(sx, sy, 3, color);

    // PRN label
    tft->setTextColor(WHITE);
    tft->setTextSize(1);
    tft->setCursor(sx + 4, sy - 3);
    tft->print(sats[i].prn);
  }
}

// Signal strength bar chart
void drawSignalBars(int x, int y, int w, int h) {
  int barW = max(1, (w - 2) / max(1, satCount));
  int gap = 1;
  if (barW > 3) { barW -= gap; } else { gap = 0; }

  for (int i = 0; i < satCount && i * (barW + gap) < w; i++) {
    int barH = map(sats[i].snr, 0, 50, 0, h);
    barH = constrain(barH, 0, h);

    uint16_t color;
    if (sats[i].snr == 0) color = GRAY;
    else if (sats[i].snr < 20) color = RED;
    else if (sats[i].snr < 35) color = YELLOW;
    else color = GREEN;

    int bx = x + i * (barW + gap);
    if (barH > 0)
      tft->fillRect(bx, y + h - barH, barW, barH, color);
  }
}

// Text info panel
void drawInfoPanel(int x, int y) {
  tft->setTextSize(1);
  tft->setTextColor(WHITE);

  // Time
  tft->setCursor(x, y);
  tft->print("UTC ");
  tft->setTextColor(CYAN);
  tft->print(timeStr);

  // Fix status
  tft->setCursor(x, y + 12);
  tft->setTextColor(WHITE);
  tft->print("FIX ");
  if (fixQuality > 0) {
    tft->setTextColor(GREEN);
    tft->print("3D");
  } else {
    tft->setTextColor(RED);
    tft->print("NO");
  }

  // Satellite counts
  tft->setCursor(x, y + 24);
  tft->setTextColor(WHITE);
  tft->print("SAT ");
  tft->setTextColor(GREEN);
  tft->print(satsInUse);
  tft->setTextColor(WHITE);
  tft->print("/");
  tft->setTextColor(YELLOW);
  tft->print(satsInView);

  // HDOP
  tft->setCursor(x, y + 36);
  tft->setTextColor(WHITE);
  tft->print("HDP ");
  if (hdop < 2.0) tft->setTextColor(GREEN);
  else if (hdop < 5.0) tft->setTextColor(YELLOW);
  else tft->setTextColor(RED);
  tft->print(hdop, 1);

  // Coordinates
  if (fixQuality > 0) {
    tft->setCursor(x, y + 52);
    tft->setTextColor(WHITE);
    tft->print("LAT ");
    tft->setTextColor(CYAN);
    tft->print(latStr);
    tft->print(latDir);

    tft->setCursor(x, y + 64);
    tft->setTextColor(WHITE);
    tft->print("LON ");
    tft->setTextColor(CYAN);
    tft->print(lonStr);
    tft->print(lonDir);

    tft->setCursor(x, y + 76);
    tft->setTextColor(WHITE);
    tft->print("ALT ");
    tft->setTextColor(CYAN);
    tft->print(altStr);
    tft->print("m");
  }
}

unsigned long lastDraw = 0;
int linesReceived = 0;

void setup() {
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);

  Serial.begin(115200);

  tft->begin();
  delay(100);
  tft->setRotation(1);
  tft->fillScreen(BLACK);

  // Title
  tft->setTextSize(1);
  tft->setTextColor(CYAN);
  tft->setCursor(70, 2);
  tft->print("GPS SATELLITE TRACKER");
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (linePos > 0) {
        lineBuf[linePos] = '\0';
        processLine(lineBuf);
        linesReceived++;
        linePos = 0;
      }
    } else if (linePos < 127) {
      lineBuf[linePos++] = c;
    }
  }

  // Redraw every 1 second
  if (millis() - lastDraw >= 1000) {
    lastDraw = millis();

    // Clear main area (leave title)
    tft->fillRect(0, 12, 240, 123, BLACK);

    // Sky plot on the left (center at 60,72, radius 48)
    drawSkyPlot(58, 72, 46);

    // Info panel on the right
    drawInfoPanel(125, 16);

    // Signal bars at bottom right
    drawSignalBars(125, 100, 110, 30);

    // Data indicator bottom-left
    tft->setTextSize(1);
    tft->setTextColor(linesReceived > 0 ? GREEN : RED);
    tft->setCursor(2, 126);
    tft->print("NMEA:");
    tft->print(linesReceived);
    tft->print(" S:");
    tft->print(satCount);
  }
}
