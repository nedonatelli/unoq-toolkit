TFT Display
===========

The project supports an **Adafruit Mini PiTFT 135x240** (ST7789 driver) connected
to the Arduino UNO Q over SPI.

Wiring
------

======= ====== ===========================
Display UNO Q Notes
======= ====== ===========================
SCK     D13    SPI clock
MOSI    D11    SPI data
CS      D10    Chip select
DC      D9     Data/command select
RST     D8     Display reset
BL      D7     Backlight (HIGH = on)
VIN     3.3V   Power
GND     GND    Ground
======= ====== ===========================

Library
-------

Uses **GFX Library for Arduino** (``Arduino_GFX``). The Adafruit ST7789 library
does not compile on Zephyr due to a missing ``pins_arduino.h`` header.

ST7789 GRAM offsets for the 135x240 panel::

    col_offset1=52, row_offset1=40, col_offset2=53, row_offset2=40

Hardware SPI Patch
------------------

The Arduino_GFX library defaults to ``SPI_MODE2`` for unknown platforms in
``Arduino_ST7789.cpp``. The ST7789 requires ``SPI_MODE0``. To enable hardware
SPI, patch the installed library:

.. code-block:: text

   ~/Documents/Arduino/libraries/GFX_Library_for_Arduino/src/display/Arduino_ST7789.cpp

Change ``SPI_MODE2`` to ``SPI_MODE0`` in the ``begin()`` method.

.. warning::

   Reinstalling or updating the GFX Library for Arduino will overwrite this
   patch. Re-apply it after any library update.

Sketches
--------

tft_hwspi (Hardware SPI)
~~~~~~~~~~~~~~~~~~~~~~~~~

Spinning 3D wireframe cube using hardware SPI at 60 MHz.

- **Rendering**: Fixed-point integer math with a 256-entry sine lookup table.
  Zero floating-point operations in the render loop.
- **Buffering**: 160x120 partial ``Arduino_Canvas`` centered on the display.
  A full 240x135 canvas (64 KB) is too slow to flush every frame even with
  hardware SPI.
- **Requires**: The SPI_MODE0 library patch described above.

tft_swspi (Software SPI)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Same spinning cube using software (bit-banged) SPI.

- **Rendering**: Floating-point math with ``sin()``/``cos()``.
- **Buffering**: Direct erase-and-redraw — erases the previous frame's edges
  in black, then draws the new edges. No off-screen canvas needed.
- **No library patch required**, but roughly 10--50x slower than hardware SPI.
  Frame rate drops noticeably when edges are longest (cube at diagonal
  orientation).

Performance Tips
----------------

- **HW SPI at 60 MHz** is the fastest reliable clock for this board + display
  combination. Higher values were not tested.
- **Partial canvas** is the sweet spot: consistent frame rate without flicker,
  and much less data to push than a full-screen buffer.
- **Fixed-point math** (10-bit fractional, ``FP_SHIFT=10``) keeps the CPU out
  of the FPU for the inner loop. The 256-entry sine LUT trades 512 bytes of
  flash for ~6x faster trig.
- **Software SPI** is a useful fallback that works without patching the library,
  but should only be used when hardware SPI is unavailable.
