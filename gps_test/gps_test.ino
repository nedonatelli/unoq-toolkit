// GPS connection test — blinks LED matrix when NMEA data is received
// GPS TX -> D0 (RX), GPS RX -> D1 (TX), VCC -> 3.3V, GND -> GND
// U-blox M10 defaults to 9600 baud
#include <Arduino_LED_Matrix.h>

Arduino_LED_Matrix matrix;
uint32_t frame[4] = {0, 0, 0, 0};

// Set a pixel in the 13x8 LED matrix frame
void setPixel(int col, int row) {
  int i = row * 13 + col;
  frame[i / 32] |= (1 << (31 - (i % 32)));
}

void clearFrame() {
  frame[0] = frame[1] = frame[2] = frame[3] = 0;
}

// Show a progress bar on row 0: length = number of chars received (max 13)
int charCount = 0;
bool gotLine = false;
char lineBuf[128];
int linePos = 0;

const long baudRates[] = {9600, 38400, 115200};
const int numBauds = 3;
int currentBaud = 0;
unsigned long baudStartTime = 0;

void showBaudIndex(int idx) {
  // Show which baud rate we're trying: 1, 2, or 3 dots on row 7
  clearFrame();
  for (int c = 0; c <= idx; c++) setPixel(c, 7);
  matrix.loadFrame(frame);
}

void setup() {
  matrix.begin();

  // Show all LEDs briefly to confirm sketch is running
  frame[0] = 0xFFFFFFFF;
  frame[1] = 0xFFFFFFFF;
  frame[2] = 0xFFFFFFFF;
  frame[3] = 0x000000FF;
  matrix.loadFrame(frame);
  delay(1000);

  Serial.begin(baudRates[0]);
  baudStartTime = millis();
  showBaudIndex(0);
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    charCount++;

    if (c == '\n' || c == '\r') {
      if (linePos > 0) {
        lineBuf[linePos] = '\0';
        gotLine = true;
        linePos = 0;
      }
    } else if (linePos < 127) {
      lineBuf[linePos++] = c;
    }
  }

  clearFrame();

  if (gotLine) {
    // Row 0: solid bar = we're receiving complete NMEA sentences
    for (int c = 0; c < 13; c++) setPixel(c, 0);

    // Row 2-3: show "GP" if line starts with $GP, "GN" if $GN
    if (lineBuf[0] == '$' && lineBuf[1] == 'G') {
      // Row 2: fill proportional to line length (max 80 chars -> 13 cols)
      int bars = min(13, (int)(strlen(lineBuf) * 13 / 80));
      for (int c = 0; c < bars; c++) setPixel(c, 2);
    }

    // Row 4: blink on/off each sentence
    static bool toggle = false;
    toggle = !toggle;
    if (toggle) {
      for (int c = 0; c < 13; c++) setPixel(c, 4);
    }

    // Row 6: number of chars received mod 13 as a moving dot
    setPixel(charCount % 13, 6);

    gotLine = false;
  } else {
    // No data yet — try next baud rate after 5 seconds
    if (millis() - baudStartTime > 5000 && !gotLine) {
      currentBaud = (currentBaud + 1) % numBauds;
      Serial.end();
      Serial.begin(baudRates[currentBaud]);
      baudStartTime = millis();
      showBaudIndex(currentBaud);
    }
    // Single blinking dot
    static unsigned long lastBlink = 0;
    static bool on = false;
    if (millis() - lastBlink > 500) {
      on = !on;
      lastBlink = millis();
    }
    if (on) setPixel(0, 0);
    // Show baud index on bottom row
    for (int c = 0; c <= currentBaud; c++) setPixel(c, 7);
  }

  matrix.loadFrame(frame);
  delay(100);
}
