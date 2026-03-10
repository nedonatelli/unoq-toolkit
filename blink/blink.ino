// ADC noise-seeded bouncing 2x2 square
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;

int x, y;
int dx, dy;

uint32_t adcNoiseSeed() {
  uint32_t seed = 0;
  for (int i = 0; i < 32; i++) {
    seed = (seed << 1) | (analogRead(A0) & 1);
  }
  return seed;
}

void gridToFrame(uint8_t grid[8][13], uint32_t* frame) {
  frame[0] = frame[1] = frame[2] = frame[3] = 0;
  for (int r = 0; r < 8; r++) {
    for (int c = 0; c < 13; c++) {
      int bit = r * 13 + c;
      if (grid[r][c]) {
        frame[bit / 32] |= (1UL << (31 - (bit % 32)));
      }
    }
  }
}

void setup() {
  matrix.begin();
  randomSeed(adcNoiseSeed());

  // Random starting position (within bounds for 2x2)
  x = random(0, 12);  // 0..11 so x+1 <= 12
  y = random(0, 7);   // 0..6 so y+1 <= 7

  // Random velocity: -1 or +1 for each axis
  dx = random(2) ? 1 : -1;
  dy = random(2) ? 1 : -1;
}

void loop() {
  uint8_t grid[8][13] = {0};

  // Draw 2x2 square
  grid[y][x] = 1;
  grid[y][x+1] = 1;
  grid[y+1][x] = 1;
  grid[y+1][x+1] = 1;

  uint32_t frame[4];
  gridToFrame(grid, frame);
  matrix.loadFrame(frame);

  // Move
  x += dx;
  y += dy;

  // Bounce off edges
  if (x <= 0 || x >= 11) dx = -dx;
  if (y <= 0 || y >= 6) dy = -dy;

  // Clamp just in case
  if (x < 0) x = 0;
  if (x > 11) x = 11;
  if (y < 0) y = 0;
  if (y > 6) y = 6;

  delay(80);
}
