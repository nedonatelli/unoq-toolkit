// Side-scroller runner game — jump over obstacles with the joystick
// VRY -> A0 (push up to jump)
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;

const int COLS = 13;
const int ROWS = 8;
const int GROUND = 7;       // ground row
const int PLAYER_COL = 2;   // player's fixed column
const int JUMP_THRESHOLD = 200;

// Player state
float playerY;
float velY;
bool onGround;
const float GRAVITY = 0.08;
const float JUMP_VEL = -1.0;

// Obstacles: array of heights per column (0 = no obstacle)
int obstacles[COLS];
int scrollCounter;
int scrollRate;     // frames between scrolls (lower = faster)
int score;
bool gameOver;
int spawnCooldown;  // columns to skip after spawning an obstacle

int centerY;  // calibrated joystick center

void setPixel(uint32_t* frame, int r, int c) {
  if (r < 0 || r >= ROWS || c < 0 || c >= COLS) return;
  int bit = r * COLS + c;
  frame[bit / 32] |= (1UL << (31 - (bit % 32)));
}

void resetGame() {
  playerY = GROUND - 1;
  velY = 0;
  onGround = true;
  scrollCounter = 0;
  scrollRate = 8;
  score = 0;
  gameOver = false;
  spawnCooldown = 0;
  for (int i = 0; i < COLS; i++) obstacles[i] = 0;
}

void drawFrame() {
  uint32_t frame[4] = {0, 0, 0, 0};

  // Draw ground
  for (int c = 0; c < COLS; c++)
    setPixel(frame, GROUND, c);

  // Draw obstacles
  for (int c = 0; c < COLS; c++) {
    for (int h = 0; h < obstacles[c]; h++)
      setPixel(frame, GROUND - 1 - h, c);
  }

  // Draw player (2 pixels tall)
  int py = (int)playerY;
  setPixel(frame, py, PLAYER_COL);
  setPixel(frame, py - 1, PLAYER_COL);

  matrix.loadFrame(frame);
}

bool checkCollision() {
  int py = (int)playerY;
  // Player occupies (py, PLAYER_COL) and (py-1, PLAYER_COL)
  int obsHeight = obstacles[PLAYER_COL];
  if (obsHeight > 0) {
    // Obstacle top is at row (GROUND - 1 - (obsHeight-1)) = GROUND - obsHeight
    int obsTop = GROUND - obsHeight;
    // Player bottom is at py, player top is at py-1
    if (py >= obsTop) return true;
  }
  return false;
}

void showGameOver() {
  // Flash all LEDs 3 times
  uint32_t allOn[4] = {0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFF000000};
  uint32_t allOff[4] = {0, 0, 0, 0};
  for (int i = 0; i < 3; i++) {
    matrix.loadFrame(allOn);
    delay(200);
    matrix.loadFrame(allOff);
    delay(200);
  }

  // Show score as binary dots on bottom row
  uint32_t scoreFrame[4] = {0, 0, 0, 0};
  for (int c = 0; c < COLS && c < score; c++)
    setPixel(scoreFrame, GROUND, COLS - 1 - c);
  matrix.loadFrame(scoreFrame);
  delay(2000);
}

void setup() {
  matrix.begin();

  // Calibrate joystick Y center
  long sum = 0;
  for (int i = 0; i < 32; i++) {
    sum += analogRead(A0);
    delay(5);
  }
  centerY = sum / 32;

  randomSeed(analogRead(A0) ^ (analogRead(A1) << 8));
  resetGame();
}

void loop() {
  if (gameOver) {
    showGameOver();
    // Wait for joystick push to restart
    while (abs(analogRead(A0) - centerY) < JUMP_THRESHOLD) delay(50);
    resetGame();
    return;
  }

  // Read joystick
  int ry = analogRead(A0) - centerY;

  // Jump if pushing up (negative Y) and on ground
  if (ry < -JUMP_THRESHOLD && onGround) {
    velY = JUMP_VEL;
    onGround = false;
  }

  // Apply gravity
  velY += GRAVITY;
  playerY += velY;

  // Land on ground
  if (playerY >= GROUND - 1) {
    playerY = GROUND - 1;
    velY = 0;
    onGround = true;
  }

  // Scroll obstacles
  scrollCounter++;
  if (scrollCounter >= scrollRate) {
    scrollCounter = 0;

    // Shift everything left
    for (int c = 0; c < COLS - 1; c++)
      obstacles[c] = obstacles[c + 1];

    // Spawn new obstacle at right edge, but enforce a gap after each one
    if (spawnCooldown > 0) {
      obstacles[COLS - 1] = 0;
      spawnCooldown--;
    } else if (random(100) < 30) {
      obstacles[COLS - 1] = random(1, 3);  // height 1-2
      spawnCooldown = 3;  // guarantee 3 empty columns after every obstacle
    } else {
      obstacles[COLS - 1] = 0;
    }

    score++;

    // Speed up every 20 points
    if (score % 20 == 0 && scrollRate > 3)
      scrollRate--;
  }

  // Check collision
  if (checkCollision()) {
    gameOver = true;
    return;
  }

  drawFrame();
  delay(40);
}
