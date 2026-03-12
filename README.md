# unoq-toolkit

A collection of tools for the **Arduino UNO Q** (STM32U585 Cortex-M33, Zephyr RTOS).

## LED Matrix Animator

A desktop GUI for designing, previewing, and uploading LED matrix patterns and animations.

## Features

- **Visual grid editor** — Click and drag to draw on a 13x8 LED matrix
- **Multi-frame timeline** — Create animations with per-frame durations; drag to reorder frames
- **Preset shapes** — Heart, Smiley, Star, Arrow, Check, X, Diamond, Music Note, Skull
- **Preset animations** — Heartbeat, Rain, Wave, Pulse, Scroll HI, Snake, Firework
- **Live sketches** — Generative Arduino code that runs directly on the board:
  - ADC Noise Random, ADC Noise Rain, ADC Noise Life (Game of Life), Bouncing Square, Bouncing Spinner
- **Preview mode** — Play back animations in the GUI before uploading
- **One-click upload** — Compiles and flashes via `arduino-cli` and OpenOCD

## Requirements

- Python 3.10+ (uses `tkinter`, included with most Python installations)
- [`arduino-cli`](https://arduino.github.io/arduino-cli/) installed and on PATH
- Arduino Zephyr core installed: `arduino-cli core install arduino:zephyr`
- Arduino UNO Q connected via USB

## Quick Start

```bash
python gui.py
```

1. Draw a pattern on the grid (click/drag to toggle LEDs)
2. Add frames with **+** or **Dup** for animations
3. Set per-frame duration in milliseconds
4. Click **Preview** to see the animation in the GUI
5. Click **Upload** to compile and flash to the board

### Loading Presets

- **Shapes** dropdown → **Load**: replaces the current frame with a static shape
- **Animations** dropdown → **Load**: replaces the entire timeline with a multi-frame animation
- **Live** dropdown → **Upload**: compiles and uploads a generative .ino sketch directly

## Project Structure

```
├── gui.py                  # Main application (editor, presets, upload)
├── blink/
│   └── blink.ino           # Auto-generated sketch (overwritten on each upload)
├── board/
│   └── wifi_monitor.py     # Linux-side Bridge RPC WiFi monitor (runs on-board)
├── wifi_scan.py            # Standalone ADB-based WiFi scanner + LED display
├── .gitignore
└── README.md
```

## Board Notes

- **No USB Serial**: `Serial` maps to hardware UART (usart1), not USB CDC. The USB port is programming-only.
- **Upload tool**: OpenOCD over USB (`remoteocd`)
- **FQBN**: `arduino:zephyr:unoq`
- **LED Matrix format**: 104 LEDs packed into 4x `uint32_t`, MSB-first, row-major
- **Zephyr API quirk**: `random()` with no arguments is unavailable — use `random(max)` or `random(min, max)`
- **ADC entropy**: Live sketches read the LSB of `analogRead(A0)` to build a hardware random seed
- **Bootloader recovery**: If the board stops responding, burn the bootloader:
  ```bash
  arduino-cli burn-bootloader --fqbn arduino:zephyr:unoq -p PORT -P openocd
  ```

## Configuration

Edit the constants at the top of `gui.py` to match your setup:

```python
PORT = "/dev/cu.usbmodem19087929472"  # Your board's USB port
FQBN = "arduino:zephyr:unoq"          # Board identifier
```

Find your port with:
```bash
arduino-cli board list
```
