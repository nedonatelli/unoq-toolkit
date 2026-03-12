LED Matrix Animator
===================

The LED Matrix Animator is a desktop GUI for designing, previewing, and uploading
LED matrix patterns and animations to the Arduino UNO Q.

Features
--------

- **Visual grid editor** — Click and drag to draw on a 13x8 LED matrix
- **Multi-frame timeline** — Create animations with per-frame durations; drag to reorder frames
- **Preset shapes** — Heart, Smiley, Star, Arrow, Check, X, Diamond, Music Note, Skull
- **Preset animations** — Heartbeat, Rain, Wave, Pulse, Scroll HI, Snake, Firework
- **Live sketches** — Generative Arduino code that runs directly on the board
- **Preview mode** — Play back animations in the GUI before uploading
- **One-click upload** — Compiles and flashes via ``arduino-cli`` and OpenOCD

Preset Shapes
-------------

Static patterns that replace the current frame in the editor:

- Heart, Smiley, Star, Arrow, Check, X, Diamond, Music Note, Skull

Use the **Shapes** dropdown and click **Load** to apply.

Preset Animations
-----------------

Multi-frame animations that replace the entire timeline:

- Heartbeat, Rain, Wave, Pulse, Scroll HI, Snake, Firework

Use the **Animations** dropdown and click **Load** to apply.

Live Sketches
-------------

Generative Arduino sketches that compile and upload directly to the board.
These run natively on the STM32 and produce dynamic, non-repeating patterns:

- **ADC Noise Random** — Random LED patterns seeded from analog noise
- **ADC Noise Rain** — Falling rain effect driven by hardware entropy
- **ADC Noise Life** — Conway's Game of Life seeded from ADC noise
- **Bouncing Square** — A square that bounces around the matrix
- **Bouncing Spinner** — A rotating line that bounces around the matrix

Use the **Live** dropdown and click **Upload** to compile and flash.

How It Works
------------

The animator generates an Arduino ``.ino`` sketch from your frame data, then uses
``arduino-cli`` to compile and upload it via OpenOCD. The LED matrix is controlled
through the ``Arduino_LED_Matrix`` library.

Each frame is packed into 4x ``uint32_t`` values (MSB-first, row-major) representing
the 104 LEDs (13 columns x 8 rows).
