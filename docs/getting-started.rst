Getting Started
===============

Requirements
------------

- Python 3.10+ (uses ``tkinter``, included with most Python installations)
- `arduino-cli <https://arduino.github.io/arduino-cli/>`_ installed and on PATH
- Arduino Zephyr core installed::

    arduino-cli core install arduino:zephyr

- Arduino UNO Q connected via USB

Installation
------------

Clone the repository::

    git clone https://github.com/nedonatelli/unoq-toolkit.git
    cd unoq-toolkit

No additional Python packages are required — the tools use only the standard library.

Quick Start
-----------

Launch the LED Matrix Animator::

    python gui.py

1. Draw a pattern on the grid (click/drag to toggle LEDs)
2. Add frames with **+** or **Dup** for animations
3. Set per-frame duration in milliseconds
4. Click **Preview** to see the animation in the GUI
5. Click **Upload** to compile and flash to the board

Configuration
-------------

Edit the constants at the top of ``gui.py`` to match your setup::

    PORT = "/dev/cu.usbmodem19087929472"  # Your board's USB port
    FQBN = "arduino:zephyr:unoq"          # Board identifier

Find your port with::

    arduino-cli board list
