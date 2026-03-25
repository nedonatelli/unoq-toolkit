// System stats display on SSD1306 OLED via Bridge RPC.
// Linux side pushes CSV stats: "uptime,cpu_temp,mem_used,mem_total,ip_addr"
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Arduino_RouterBridge.h>

Adafruit_SSD1306 display(128, 64, &Wire, -1);

String uptime_str = "--";
String cpu_temp = "--";
String mem_used = "--";
String mem_total = "--";
String ip_addr = "--";

void drawStats() {
  display.clearDisplay();

  // Yellow zone (top 16px): title
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 4);
  display.print("UNO Q  ");
  display.print(ip_addr);

  // Blue zone (below 16px): stats
  display.drawLine(0, 16, 127, 16, SSD1306_WHITE);

  // Uptime
  display.setCursor(0, 20);
  display.print("Uptime: ");
  display.print(uptime_str);

  // CPU temp
  display.setCursor(0, 32);
  display.print("CPU:    ");
  display.print(cpu_temp);
  display.print(" C");

  // Memory bar
  display.setCursor(0, 44);
  display.print("Mem:    ");
  display.print(mem_used);
  display.print("/");
  display.print(mem_total);
  display.print(" MB");

  // Memory bar graphic
  long used = atol(mem_used.c_str());
  long total = atol(mem_total.c_str());
  if (total > 0) {
    int barW = map(used, 0, total, 0, 100);
    display.drawRect(0, 56, 104, 8, SSD1306_WHITE);
    display.fillRect(2, 58, barW, 4, SSD1306_WHITE);
  }

  display.display();
}

// "uptime,cpu_temp,mem_used,mem_total,ip_addr"
String set_stats(String csv) {
  int parts[4];
  int start = 0, idx = 0;
  for (int i = 0; i <= (int)csv.length() && idx < 5; i++) {
    if (i == (int)csv.length() || csv[i] == ',') {
      String val = csv.substring(start, i);
      switch (idx) {
        case 0: uptime_str = val; break;
        case 1: cpu_temp = val; break;
        case 2: mem_used = val; break;
        case 3: mem_total = val; break;
        case 4: ip_addr = val; break;
      }
      idx++;
      start = i + 1;
    }
  }
  drawStats();
  return String("ok");
}

void setup() {
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(10, 28);
  display.println("Waiting for stats...");
  display.display();

  Bridge.begin(460800);
  Bridge.provide("set_stats", set_stats);
}

void loop() {
}