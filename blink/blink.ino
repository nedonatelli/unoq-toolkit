// ADC noise-seeded rain effect
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;
uint8_t grid[8][13] = {0};

uint32_t adcNoiseSeed() {
  uint32_t seed = 0;
  for (int i = 0; i < 32; i++) {
    seed = (seed << 1) | (analogRead(A0) & 1);
  }
  return seed;
}

void gridToFrame(uint32_t* frame) {
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
}

void loop() {
  // Shift all rows down
  for (int r = 7; r > 0; r--) {
    for (int c = 0; c < 13; c++) {
      grid[r][c] = grid[r-1][c];
    }
  }
  // Clear top row and add new random drops
  for (int c = 0; c < 13; c++) {
    grid[0][c] = 0;
  }
  // Re-seed from ADC noise and spawn 1-3 drops
  randomSeed(adcNoiseSeed());
  int nDrops = random(1, 4);
  for (int i = 0; i < nDrops; i++) {
    grid[0][random(13)] = 1;
  }

  uint32_t frame[4];
  gridToFrame(frame);
  matrix.loadFrame(frame);
  delay(120);
}
