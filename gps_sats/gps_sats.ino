// GPS Satellite Tracker — LED matrix visualization
// Parses NMEA GGA for satellites in use, GSV for satellites in view
// GPS TX -> D0 (RX), VCC -> 3.3V, GND -> GND
// u-blox M10 at 115200 baud
#include <Arduino_LED_Matrix.h>

Arduino_LED_Matrix matrix;
uint32_t frame[4] = {0, 0, 0, 0};

void setPixel(int col, int row) {
  if (col < 0 || col > 12 || row < 0 || row > 7) return;
  int i = row * 13 + col;
  frame[i / 32] |= (1 << (31 - (i % 32)));
}

void clearFrame() {
  frame[0] = frame[1] = frame[2] = frame[3] = 0;
}

// NMEA parser state
char lineBuf[128];
int linePos = 0;

// Satellite data
int satsInUse = 0;     // from GGA field 7
int satsInView = 0;    // from GSV field 3
int fixQuality = 0;    // from GGA field 6 (0=no fix, 1=GPS, 2=DGPS)

// Parse a comma-separated field from NMEA sentence
// Returns pointer to start of field, writes length to len
int getField(const char *sentence, int fieldNum, char *out, int maxLen) {
  int field = 0;
  int i = 0;
  int start = 0;

  while (sentence[i]) {
    if (sentence[i] == ',' || sentence[i] == '*') {
      if (field == fieldNum) {
        int len = i - start;
        if (len > maxLen - 1) len = maxLen - 1;
        memcpy(out, sentence + start, len);
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
  char val[16];
  // Field 6: fix quality
  if (getField(line, 6, val, sizeof(val)) > 0)
    fixQuality = atoi(val);
  else
    fixQuality = 0;

  // Field 7: number of satellites in use
  if (getField(line, 7, val, sizeof(val)) > 0)
    satsInUse = atoi(val);
}

void parseGSV(const char *line) {
  char val[16];
  // Field 3: total satellites in view
  if (getField(line, 3, val, sizeof(val)) > 0)
    satsInView = atoi(val);
}

void processLine(const char *line) {
  // Match GGA sentences (GPGGA, GNGGA, etc.)
  if (strstr(line, "GGA")) parseGGA(line);
  // Match GSV sentences — use first one for total in view
  if (strstr(line, "GSV")) parseGSV(line);
}

void drawDisplay() {
  clearFrame();

  // Row 0-2: Satellites in USE — filled bar graph
  // Scale: each column = 1 satellite, up to 13
  // Row 0: top of bar (fills down as count increases)
  //   1-13 sats: row 2 only
  //   14-26 sats: rows 1-2
  //   27+: rows 0-2
  int cols = min(13, satsInUse);
  for (int c = 0; c < cols; c++) setPixel(c, 2);
  if (satsInUse > 13) {
    int extra = min(13, satsInUse - 13);
    for (int c = 0; c < extra; c++) setPixel(c, 1);
  }
  if (satsInUse > 26) {
    int extra2 = min(13, satsInUse - 26);
    for (int c = 0; c < extra2; c++) setPixel(c, 0);
  }

  // Row 4-6: Satellites in VIEW — outlined bar graph
  // Scale: each column = 2 satellites, up to 26
  int viewCols = min(13, (satsInView + 1) / 2);
  for (int c = 0; c < viewCols; c++) setPixel(c, 5);
  if (satsInView > 26) {
    int extra = min(13, (satsInView - 26 + 1) / 2);
    for (int c = 0; c < extra; c++) setPixel(c, 4);
  }

  // Row 7: Fix status indicator
  if (fixQuality == 0) {
    // No fix — single blinking dot
    static unsigned long lastBlink = 0;
    static bool on = false;
    if (millis() - lastBlink > 500) {
      on = !on;
      lastBlink = millis();
    }
    if (on) setPixel(0, 7);
  } else {
    // Has fix — solid dots (count = fix quality)
    int dots = min(13, fixQuality);
    for (int c = 0; c < dots; c++) setPixel(c, 7);
  }

  matrix.loadFrame(frame);
}

void setup() {
  matrix.begin();
  Serial.begin(115200);

  // Startup animation — fill from bottom
  for (int row = 7; row >= 0; row--) {
    clearFrame();
    for (int r = row; r <= 7; r++)
      for (int c = 0; c < 13; c++) setPixel(c, r);
    matrix.loadFrame(frame);
    delay(80);
  }
  delay(500);
  clearFrame();
  matrix.loadFrame(frame);
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

  drawDisplay();
  delay(200);
}
