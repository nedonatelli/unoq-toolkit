// Spinning 3D cube on Adafruit Mini PiTFT 135x240 (ST7789)
// HW SPI + partial canvas + fixed-point math (no floats in render loop)
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

#define BLACK   0x0000
#define CYAN    0x07FF
#define YELLOW  0xFFE0
#define MAGENTA 0xF81F

#define TFT_CS   10
#define TFT_DC    9
#define TFT_RST   8
#define TFT_BL    7

Arduino_DataBus *bus = new Arduino_HWSPI(TFT_DC, TFT_CS, &SPI, 60000000);
Arduino_ST7789 *tft = new Arduino_ST7789(bus, TFT_RST, 0, true, 135, 240, 52, 40, 53, 40);

const int CVW = 160, CVH = 120;
const int CVX = 40, CVY = 7;
Arduino_Canvas *canvas = new Arduino_Canvas(CVW, CVH, tft, CVX, CVY);

// Fixed-point: 10 fractional bits (multiply by 1024)
#define FP_SHIFT 10
#define FP_ONE   (1 << FP_SHIFT)

// 256-entry sine table, values in fixed-point [-1024..1024]
// Covers 0..2*PI in 256 steps
static const int16_t sinTab[256] PROGMEM = {
     0,   25,   50,   75,  100,  125,  150,  175,
   199,  224,  248,  273,  297,  321,  344,  368,
   391,  414,  437,  460,  482,  504,  526,  547,
   568,  589,  609,  629,  649,  668,  687,  706,
   724,  741,  758,  775,  791,  807,  822,  837,
   851,  865,  878,  891,  903,  915,  926,  936,
   946,  955,  964,  972,  980,  987,  993,  999,
  1004, 1009, 1013, 1016, 1019, 1021, 1023, 1024,
  1024, 1024, 1023, 1021, 1019, 1016, 1013, 1009,
  1004,  999,  993,  987,  980,  972,  964,  955,
   946,  936,  926,  915,  903,  891,  878,  865,
   851,  837,  822,  807,  791,  775,  758,  741,
   724,  706,  687,  668,  649,  629,  609,  589,
   568,  547,  526,  504,  482,  460,  437,  414,
   391,  368,  344,  321,  297,  273,  248,  224,
   199,  175,  150,  125,  100,   75,   50,   25,
     0,  -25,  -50,  -75, -100, -125, -150, -175,
  -199, -224, -248, -273, -297, -321, -344, -368,
  -391, -414, -437, -460, -482, -504, -526, -547,
  -568, -589, -609, -629, -649, -668, -687, -706,
  -724, -741, -758, -775, -791, -807, -822, -837,
  -851, -865, -878, -891, -903, -915, -926, -936,
  -946, -955, -964, -972, -980, -987, -993, -999,
 -1004,-1009,-1013,-1016,-1019,-1021,-1023,-1024,
 -1024,-1024,-1023,-1021,-1019,-1016,-1013,-1009,
 -1004, -999, -993, -987, -980, -972, -964, -955,
  -946, -936, -926, -915, -903, -891, -878, -865,
  -851, -837, -822, -807, -791, -775, -758, -741,
  -724, -706, -687, -668, -649, -629, -609, -589,
  -568, -547, -526, -504, -482, -460, -437, -414,
  -391, -368, -344, -321, -297, -273, -248, -224,
  -199, -175, -150, -125, -100,  -75,  -50,  -25
};

inline int16_t fpSin(uint8_t angle) { return (int16_t)pgm_read_word(&sinTab[angle]); }
inline int16_t fpCos(uint8_t angle) { return (int16_t)pgm_read_word(&sinTab[(angle + 64) & 255]); }

// Fixed-point multiply: (a * b) >> FP_SHIFT
inline int32_t fpMul(int32_t a, int32_t b) { return (a * b) >> FP_SHIFT; }

// Cube vertices in fixed-point: ±FP_ONE
const int32_t verts[8][3] = {
  {-FP_ONE,-FP_ONE,-FP_ONE}, { FP_ONE,-FP_ONE,-FP_ONE},
  { FP_ONE, FP_ONE,-FP_ONE}, {-FP_ONE, FP_ONE,-FP_ONE},
  {-FP_ONE,-FP_ONE, FP_ONE}, { FP_ONE,-FP_ONE, FP_ONE},
  { FP_ONE, FP_ONE, FP_ONE}, {-FP_ONE, FP_ONE, FP_ONE}
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

uint8_t angleX = 0, angleY = 0, angleZ = 0;

const int CX = CVW / 2;
const int CY = CVH / 2;
const int32_t SCALE = 40;

// Precomputed trig
int16_t sx_, cx_, sy_, cy_, sz_, cz_;

void project(int32_t x, int32_t y, int32_t z, int &screenX, int &screenY) {
  // Rotate X
  int32_t y1 = fpMul(y, cx_) - fpMul(z, sx_);
  int32_t z1 = fpMul(y, sx_) + fpMul(z, cx_);
  // Rotate Y
  int32_t x2 = fpMul(x, cy_) + fpMul(z1, sy_);
  // Rotate Z
  int32_t x3 = fpMul(x2, cz_) - fpMul(y1, sz_);
  int32_t y3 = fpMul(x2, sz_) + fpMul(y1, cz_);

  screenX = CX + (int)((x3 * SCALE) >> FP_SHIFT);
  screenY = CY + (int)((y3 * SCALE) >> FP_SHIFT);
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

  sx_ = fpSin(angleX); cx_ = fpCos(angleX);
  sy_ = fpSin(angleY); cy_ = fpCos(angleY);
  sz_ = fpSin(angleZ); cz_ = fpCos(angleZ);

  int px[8], py[8];
  for (int i = 0; i < 8; i++)
    project(verts[i][0], verts[i][1], verts[i][2], px[i], py[i]);

  for (int i = 0; i < 12; i++) {
    int a = edges[i][0], b = edges[i][1];
    canvas->drawLine(px[a], py[a], px[b], py[b], edgeColors[i]);
  }

  canvas->flush();

  angleX += 1;
  angleY += 2;
  angleZ += 1;
}
