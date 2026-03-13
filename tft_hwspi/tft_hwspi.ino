// Spinning 3D cube on Adafruit Mini PiTFT 135x240 (ST7789)
// HW SPI + partial canvas flush for fast, consistent framerate
//
// Wiring (display -> UNO Q):
//   SCK  -> D13
//   MOSI -> D11
//   CS   -> D10
//   DC   -> D9
//   RST  -> D8
//   BL   -> D7
//   VIN  -> 3.3V
//   GND  -> GND
#include <Arduino_GFX_Library.h>
#include <SPI.h>
#include <math.h>

#define BLACK   0x0000
#define CYAN    0x07FF
#define YELLOW  0xFFE0
#define MAGENTA 0xF81F

#define TFT_CS   10
#define TFT_DC    9
#define TFT_RST   8
#define TFT_BL    7

// ST7789 supports up to ~62MHz SPI
Arduino_DataBus *bus = new Arduino_HWSPI(TFT_DC, TFT_CS);
Arduino_ST7789 *tft = new Arduino_ST7789(bus, TFT_RST, 0, true, 135, 240, 52, 40, 53, 40);

// Partial canvas: 160x120 centered on the cube area
const int CVW = 160, CVH = 120;
const int CVX = 40, CVY = 7;  // top-left of canvas on screen
Arduino_Canvas *canvas = new Arduino_Canvas(CVW, CVH, tft, CVX, CVY);

float verts[8][3] = {
  {-1,-1,-1}, { 1,-1,-1}, { 1, 1,-1}, {-1, 1,-1},
  {-1,-1, 1}, { 1,-1, 1}, { 1, 1, 1}, {-1, 1, 1}
};

int edges[12][2] = {
  {0,1},{1,2},{2,3},{3,0},
  {4,5},{5,6},{6,7},{7,4},
  {0,4},{1,5},{2,6},{3,7}
};

uint16_t edgeColors[12] = {
  CYAN, CYAN, CYAN, CYAN,
  YELLOW, YELLOW, YELLOW, YELLOW,
  MAGENTA, MAGENTA, MAGENTA, MAGENTA
};

float angleX = 0, angleY = 0, angleZ = 0;

// Center of cube in canvas-local coords
const int CX = CVW / 2;
const int CY = CVH / 2;
const float SCALE = 40.0;

float sx_, cx_, sy_, cy_, sz_, cz_;

void project(float x, float y, float z, int &sx, int &sy) {
  float y1 = y * cx_ - z * sx_;
  float z1 = y * sx_ + z * cx_;
  float x2 = x * cy_ + z1 * sy_;
  float x3 = x2 * cz_ - y1 * sz_;
  float y3 = x2 * sz_ + y1 * cz_;
  sx = CX + (int)(x3 * SCALE);
  sy = CY + (int)(y3 * SCALE);
}

void setup() {
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);

  tft->begin();
  delay(100);
  tft->setRotation(1);
  tft->fillScreen(BLACK);

  canvas->begin();
}

void loop() {
  canvas->fillScreen(BLACK);

  sx_ = sin(angleX); cx_ = cos(angleX);
  sy_ = sin(angleY); cy_ = cos(angleY);
  sz_ = sin(angleZ); cz_ = cos(angleZ);

  int px[8], py[8];
  for (int i = 0; i < 8; i++)
    project(verts[i][0], verts[i][1], verts[i][2], px[i], py[i]);

  for (int i = 0; i < 12; i++) {
    int a = edges[i][0], b = edges[i][1];
    canvas->drawLine(px[a], py[a], px[b], py[b], edgeColors[i]);
  }

  canvas->flush();

  angleX += 0.03;
  angleY += 0.05;
  angleZ += 0.02;
}
