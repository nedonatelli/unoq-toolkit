Board Notes
===========

Arduino UNO Q Hardware
----------------------

- **MCU**: STM32U585 (Cortex-M33)
- **RTOS**: Zephyr
- **FQBN**: ``arduino:zephyr:unoq``
- **Upload tool**: OpenOCD over USB (``remoteocd``)

LED Matrix
----------

- **Size**: 13 columns x 8 rows (104 LEDs)
- **Frame format**: 4x ``uint32_t``, MSB-first, row-major
- **Library**: ``Arduino_LED_Matrix``

USB and Serial
--------------

``Serial`` maps to hardware UART (``usart1``), **not** USB CDC. The USB port is
programming-only — there is no USB serial console.

For standalone operation, set ``wait_linux_boot=no`` to avoid waiting for the
Linux side to boot.

Zephyr API Quirks
-----------------

- ``random()`` with no arguments is unavailable. Use ``random(max)`` or
  ``random(min, max)`` instead.
- Live sketches use the LSB of ``analogRead(A0)`` as a hardware entropy source
  for seeding the PRNG.

RGB LEDs
--------

- **LED3**: Pins PH10–PH12 (mapped to pins 48–50)
- **LED4**: Pins PH13–PH15 (mapped to pins 51–53)
- PWM polarity is inverted (255 = off, 0 = full brightness)

Bootloader Recovery
-------------------

If the board stops responding, burn the bootloader::

    arduino-cli burn-bootloader --fqbn arduino:zephyr:unoq -p PORT -P openocd
