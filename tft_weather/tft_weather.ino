// Weather display on TFT via Bridge RPC
// TFT on HW SPI (D13/D11/D10/D9/D8/D7), ST7789 240x135
//
// Bridge RPC methods:
//   set_weather -> receives CSV: "temp,high,low,humidity,wind,code,description"
//
// Run board/tft_weather.py on the Linux side.
#include <Arduino_GFX_Library.h>
#include <Arduino_RouterBridge.h>
#include <SPI.h>

#define BLACK   0x0000
#define WHITE   0xFFFF
#define YELLOW  0xFFE0
#define CYAN    0x07FF
#define BLUE    0x001F
#define GRAY    0x7BEF
#define ORANGE  0xFD20
#define DKBLUE  0x000B

#define TFT_CS   10
#define TFT_DC    9
#define TFT_RST   8
#define TFT_BL    7

Arduino_DataBus *bus = new Arduino_HWSPI(TFT_DC, TFT_CS, &SPI, 60000000);
Arduino_ST7789 *tft = new Arduino_ST7789(bus, TFT_RST, 0, true, 135, 240, 52, 40, 53, 40);

// Weather state
String temp = "--";
String high = "--";
String low = "--";
String humidity = "--";
String wind = "--";
int weatherCode = -1;
String description = "Loading...";

// WMO weather code to simple icon type
// 0=clear, 1=partly cloudy, 2=cloudy, 3=rain, 4=snow, 5=thunder
int codeToIcon(int code) {
  if (code <= 1) return 0;        // clear
  if (code <= 3) return 1;        // partly cloudy / overcast
  if (code <= 49) return 2;       // fog/cloudy
  if (code <= 69) return 3;       // rain/drizzle
  if (code <= 79) return 4;       // snow
  if (code <= 84) return 3;       // rain showers
  if (code <= 86) return 4;       // snow showers
  if (code <= 99) return 5;       // thunderstorm
  return 2;
}

void drawSun(int cx, int cy, int r) {
  tft->fillCircle(cx, cy, r, YELLOW);
  for (int a = 0; a < 360; a += 45) {
    float rad = a * 3.14159 / 180.0;
    int x1 = cx + cos(rad) * (r + 3);
    int y1 = cy + sin(rad) * (r + 3);
    int x2 = cx + cos(rad) * (r + 8);
    int y2 = cy + sin(rad) * (r + 8);
    tft->drawLine(x1, y1, x2, y2, YELLOW);
  }
}

void drawCloud(int x, int y, uint16_t color) {
  tft->fillCircle(x, y, 8, color);
  tft->fillCircle(x + 10, y - 3, 10, color);
  tft->fillCircle(x + 22, y, 8, color);
  tft->fillRoundRect(x - 8, y, 38, 12, 4, color);
}

void drawRain(int x, int y) {
  drawCloud(x, y, GRAY);
  for (int i = 0; i < 4; i++) {
    int rx = x - 2 + i * 8;
    tft->drawLine(rx, y + 14, rx - 3, y + 22, CYAN);
  }
}

void drawSnow(int x, int y) {
  drawCloud(x, y, GRAY);
  for (int i = 0; i < 4; i++) {
    int sx = x - 2 + i * 8;
    tft->fillCircle(sx, y + 18, 2, WHITE);
  }
}

void drawThunder(int x, int y) {
  drawCloud(x, y, GRAY);
  // Lightning bolt
  tft->drawLine(x + 8, y + 12, x + 4, y + 19, YELLOW);
  tft->drawLine(x + 4, y + 19, x + 10, y + 19, YELLOW);
  tft->drawLine(x + 10, y + 19, x + 6, y + 26, YELLOW);
}

void drawWeatherIcon(int x, int y, int icon) {
  switch (icon) {
    case 0: drawSun(x + 15, y + 15, 10); break;
    case 1: drawSun(x + 8, y + 10, 8); drawCloud(x + 8, y + 12, GRAY); break;
    case 2: drawCloud(x + 5, y + 10, GRAY); break;
    case 3: drawRain(x + 5, y + 5); break;
    case 4: drawSnow(x + 5, y + 5); break;
    case 5: drawThunder(x + 5, y + 2); break;
  }
}

void drawWeather() {
  tft->fillScreen(DKBLUE);

  // Location (centered)
  tft->setTextSize(1);
  tft->setTextColor(GRAY, DKBLUE);
  int locW = 16 * 6;  // "Washington, D.C." = 16 chars * 6px
  tft->setCursor((240 - locW) / 2, 2);
  tft->print("Washington, D.C.");

  // Icon + temp block — center the combined width
  // Icon ~40px wide, gap 10px, temp ~(digits*24 + 12)px for "F"
  int tempW = temp.length() * 24 + 12;  // size4 digits + size2 "F"
  int blockW = 44 + 10 + tempW;
  int blockX = (240 - blockW) / 2;

  // Weather icon
  int icon = codeToIcon(weatherCode);
  drawWeatherIcon(blockX, 16, icon);

  // Current temp (big)
  tft->setTextSize(4);
  tft->setTextColor(WHITE, DKBLUE);
  int tempX = blockX + 54;
  tft->setCursor(tempX, 20);
  tft->print(temp);
  // Degree F
  tft->setTextSize(2);
  tft->setCursor(tempX + temp.length() * 24, 20);
  tft->print("F");

  // Description (centered)
  tft->setTextSize(1);
  tft->setTextColor(CYAN, DKBLUE);
  int descW = description.length() * 6;
  tft->setCursor((240 - descW) / 2, 58);
  tft->print(description);

  // Divider
  tft->drawLine(20, 72, 220, 72, GRAY);

  // Bottom stats — 3 columns evenly spaced
  tft->setTextSize(1);
  int col1 = 12, col2 = 88, col3 = 168;

  // Hi/Lo
  tft->setTextColor(ORANGE, DKBLUE);
  tft->setCursor(col1, 80);
  tft->print("Hi: ");
  tft->print(high);
  tft->print("F");

  tft->setTextColor(CYAN, DKBLUE);
  tft->setCursor(col1, 94);
  tft->print("Lo: ");
  tft->print(low);
  tft->print("F");

  // Humidity
  tft->setTextColor(WHITE, DKBLUE);
  tft->setCursor(col2, 80);
  tft->print("Humid");
  tft->setCursor(col2, 94);
  tft->print(humidity);
  tft->print("%");

  // Wind
  tft->setCursor(col3, 80);
  tft->print("Wind");
  tft->setCursor(col3, 94);
  tft->print(wind);
  tft->print(" mph");

  // Footer (centered)
  tft->setTextColor(GRAY, DKBLUE);
  int footW = 22 * 6;  // "Updated via Open-Meteo"
  tft->setCursor((240 - footW) / 2, 120);
  tft->print("Updated via Open-Meteo");
}

// CSV: "temp,high,low,humidity,wind,code,description"
String set_weather(String csv) {
  int start = 0, idx = 0;
  for (int i = 0; i <= (int)csv.length() && idx < 7; i++) {
    if (i == (int)csv.length() || csv[i] == ',') {
      String val = csv.substring(start, i);
      switch (idx) {
        case 0: temp = val; break;
        case 1: high = val; break;
        case 2: low = val; break;
        case 3: humidity = val; break;
        case 4: wind = val; break;
        case 5: weatherCode = val.toInt(); break;
        case 6: description = val; break;
      }
      idx++;
      start = i + 1;
    }
  }
  drawWeather();
  return String("ok");
}

void setup() {
  tft->begin();
  tft->setRotation(1);
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  tft->fillScreen(DKBLUE);

  tft->setTextSize(1);
  tft->setTextColor(WHITE, DKBLUE);
  tft->setCursor(10, 60);
  tft->print("Waiting for Bridge...");

  Bridge.begin(460800);
  Bridge.provide("set_weather", set_weather);

  tft->fillScreen(DKBLUE);
  tft->setCursor(10, 60);
  tft->print("Fetching weather...");
}

void loop() {
}