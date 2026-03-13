// Joystick-controlled 2x2 square on the LED matrix
// VRX -> A1, VRY -> A0
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;

const int COLS = 13;
const int ROWS = 8;
const float SPEED = 0.4;
const int DEADZONE = 150;

float posX = 5.0;
float posY = 3.0;

// Auto-calibrated center values
int centerX, centerY;

void setPixel(uint32_t* frame, int r, int c) {
  int bit = r * COLS + c;
  frame[bit / 32] |= (1UL << (31 - (bit % 32)));
}

void drawSquare(int x, int y) {
  uint32_t frame[4] = {0, 0, 0, 0};
  for (int r = y; r < y + 2 && r < ROWS; r++)
    for (int c = x; c < x + 2 && c < COLS; c++)
      setPixel(frame, r, c);
  matrix.loadFrame(frame);
}

void setup() {
  matrix.begin();

  // Calibrate: read resting position (don't touch joystick during boot)
  long sumX = 0, sumY = 0;
  for (int i = 0; i < 32; i++) {
    sumX += analogRead(A1);
    sumY += analogRead(A0);
    delay(5);
  }
  centerX = sumX / 32;
  centerY = sumY / 32;
}

void loop() {
  int rx = analogRead(A1) - centerX;
  int ry = analogRead(A0) - centerY;

  if (abs(rx) > DEADZONE) posX += (rx > 0 ? SPEED : -SPEED);
  if (abs(ry) > DEADZONE) posY += (ry > 0 ? SPEED : -SPEED);

  if (posX < 0) posX = 0;
  if (posX > COLS - 2) posX = COLS - 2;
  if (posY < 0) posY = 0;
  if (posY > ROWS - 2) posY = ROWS - 2;

  drawSquare((int)posX, (int)posY);
  delay(50);
}
