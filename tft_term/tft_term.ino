// TFT Terminal Emulator — displays shell output from Linux via Bridge RPC
// TFT on HW SPI (D13/D11/D10/D9/D8/D7), ST7789 240x135
//
// Bridge RPC methods:
//   term_write -> receives text string, appends to terminal buffer
//   term_clear -> clears the screen
//
// Run board/tft_term.py on the Linux side.
#include <Arduino_GFX_Library.h>
#include <Arduino_RouterBridge.h>
#include <SPI.h>

#define BLACK   0x0000
#define GREEN   0x07E0

#define TFT_CS   10
#define TFT_DC    9
#define TFT_RST   8
#define TFT_BL    7

// 240x135 ST7789
Arduino_DataBus *bus = new Arduino_HWSPI(TFT_DC, TFT_CS, &SPI, 60000000);
Arduino_ST7789 *tft = new Arduino_ST7789(bus, TFT_RST, 0, true, 135, 240, 52, 40, 53, 40);

// Terminal: 40 cols x 16 rows with 6x8 font
#define TERM_COLS 40
#define TERM_ROWS 16
#define CHAR_W 6
#define CHAR_H 8

char screen[TERM_ROWS][TERM_COLS + 1];
bool rowDirty[TERM_ROWS];
int cursorRow = 0;
int cursorCol = 0;

void termClear() {
  for (int r = 0; r < TERM_ROWS; r++) {
    memset(screen[r], ' ', TERM_COLS);
    screen[r][TERM_COLS] = '\0';
    rowDirty[r] = true;
  }
  cursorRow = 0;
  cursorCol = 0;
}

void termScroll() {
  for (int r = 0; r < TERM_ROWS - 1; r++) {
    memcpy(screen[r], screen[r + 1], TERM_COLS);
    rowDirty[r] = true;
  }
  memset(screen[TERM_ROWS - 1], ' ', TERM_COLS);
  rowDirty[TERM_ROWS - 1] = true;
  cursorRow = TERM_ROWS - 1;
}

void termPutChar(char c) {
  if (c == '\n') {
    cursorCol = 0;
    cursorRow++;
    if (cursorRow >= TERM_ROWS) termScroll();
  } else if (c == '\r') {
    cursorCol = 0;
  } else if (c == '\t') {
    int next = (cursorCol + 4) & ~3;
    while (cursorCol < next && cursorCol < TERM_COLS) {
      screen[cursorRow][cursorCol++] = ' ';
    }
    rowDirty[cursorRow] = true;
    if (cursorCol >= TERM_COLS) {
      cursorCol = 0;
      cursorRow++;
      if (cursorRow >= TERM_ROWS) termScroll();
    }
  } else {
    if (cursorCol >= TERM_COLS) {
      cursorCol = 0;
      cursorRow++;
      if (cursorRow >= TERM_ROWS) termScroll();
    }
    screen[cursorRow][cursorCol++] = c;
    rowDirty[cursorRow] = true;
  }
}

void termWrite(const char *text) {
  while (*text) termPutChar(*text++);
}

// Only redraw dirty rows — setTextColor with bg overwrites old pixels
void renderScreen() {
  tft->setTextSize(1);
  tft->setTextColor(GREEN, BLACK);
  for (int r = 0; r < TERM_ROWS; r++) {
    if (!rowDirty[r]) continue;
    rowDirty[r] = false;
    tft->setCursor(0, r * CHAR_H);
    for (int c = 0; c < TERM_COLS; c++) {
      tft->print(screen[r][c]);
    }
  }
}

String rpc_term_write(String text) {
  termWrite(text.c_str());
  renderScreen();
  return String("ok");
}

String rpc_term_clear(String) {
  termClear();
  tft->fillScreen(BLACK);
  renderScreen();
  return String("ok");
}

void setup() {
  tft->begin();
  tft->setRotation(1);
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  tft->fillScreen(BLACK);

  termClear();
  termWrite("TFT Terminal v1.0\n");
  termWrite("Waiting for Bridge...\n");
  renderScreen();

  Bridge.begin(460800);
  Bridge.provide("term_write", rpc_term_write);
  Bridge.provide("term_clear", rpc_term_clear);

  termWrite("Ready.\n");
  termWrite("$ ");
  renderScreen();
}

void loop() {
}