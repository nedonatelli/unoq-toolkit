#!/usr/bin/env python3
"""WiFi scanner that displays signal strength on Arduino UNO Q LED matrix"""

import subprocess
import re
import time
import os

ADB = "PLACEHOLDER_HOME_Library/Arduino15/packages/arduino/tools/adb/32.0.0/adb"
FQBN = "arduino:zephyr:unoq"
PORT = "/dev/cu.usbmodem19087929472"
SKETCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blink")

ROWS = 8
COLS = 13


def scan_wifi():
    """Scan WiFi networks via ADB and return list of (ssid, signal)."""
    result = subprocess.run(
        [ADB, "shell", "nmcli -t -f SSID,SIGNAL dev wifi list"],
        capture_output=True, text=True, timeout=15
    )
    networks = []
    for line in result.stdout.strip().split("\n"):
        if ":" in line:
            parts = line.rsplit(":", 1)
            if len(parts) == 2:
                ssid = parts[0].strip()
                try:
                    signal = int(parts[1].strip())
                except ValueError:
                    continue
                if ssid and signal > 0:
                    # Deduplicate: keep strongest signal per SSID
                    existing = {n[0]: n[1] for n in networks}
                    if ssid not in existing or signal > existing[ssid]:
                        networks = [(s, sig) for s, sig in networks if s != ssid]
                        networks.append((ssid, signal))
    # Sort by signal strength descending
    networks.sort(key=lambda x: x[1], reverse=True)
    return networks[:COLS]


def build_frame(networks):
    """Build LED matrix frame from WiFi signal data."""
    pixels = [[False] * COLS for _ in range(ROWS)]
    for col, (ssid, signal) in enumerate(networks):
        bar_height = round(signal / 100 * ROWS)
        bar_height = max(1, min(ROWS, bar_height))
        for row in range(bar_height):
            pixels[ROWS - 1 - row][col] = True
    return pixels


def pixels_to_uint32s(pixels):
    """Convert pixel grid to 4x uint32_t."""
    frame = [0, 0, 0, 0]
    for r in range(ROWS):
        for c in range(COLS):
            i = r * COLS + c
            if pixels[r][c]:
                frame[i // 32] |= (1 << (31 - (i % 32)))
    return frame


def generate_and_upload(networks):
    """Generate sketch and upload to board."""
    frame = pixels_to_uint32s(build_frame(networks))

    # Build SSID comment
    ssid_list = ", ".join(f"{s}({sig}%)" for s, sig in networks)

    sketch = f"""// WiFi Signal Strength Monitor
// Networks (L to R): {ssid_list}
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;

const uint32_t pattern[] = {{
  0x{frame[0]:08X}, 0x{frame[1]:08X}, 0x{frame[2]:08X}, 0x{frame[3]:08X}
}};

void setup() {{
  matrix.begin();
  matrix.loadFrame(pattern);
}}

void loop() {{
}}
"""
    sketch_path = os.path.join(SKETCH_DIR, "blink.ino")
    with open(sketch_path, "w") as f:
        f.write(sketch)

    # Compile
    print("  Compiling...", end=" ", flush=True)
    result = subprocess.run(
        ["arduino-cli", "compile", "--fqbn", FQBN, SKETCH_DIR],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"FAILED\n{result.stderr}")
        return False

    # Upload
    print("Uploading...", end=" ", flush=True)
    result = subprocess.run(
        ["arduino-cli", "upload", "-p", PORT, "--fqbn", FQBN, SKETCH_DIR],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"FAILED\n{result.stderr}")
        return False

    print("Done!")
    return True


def main():
    print("WiFi Signal Strength Monitor for Arduino UNO Q")
    print("=" * 50)
    print(f"Scanning WiFi via ADB and displaying top {COLS} networks")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            print("Scanning WiFi networks...")
            networks = scan_wifi()

            if not networks:
                print("  No networks found!")
                time.sleep(5)
                continue

            print(f"  Found {len(networks)} unique networks:")
            for i, (ssid, signal) in enumerate(networks):
                bar = "#" * (signal // 10)
                print(f"    {i+1:2d}. {ssid:25s} {signal:3d}% {bar}")

            generate_and_upload(networks)

            print(f"\nRefreshing in 30 seconds... (Ctrl+C to stop)\n")
            time.sleep(30)

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
