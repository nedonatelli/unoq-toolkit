WiFi & Board Tools
==================

RPC Frame Receiver (``rpc_receiver/``)
--------------------------------------

An Arduino sketch that registers a ``set_frame`` Bridge RPC method, allowing
any Linux-side script to push LED frames to the matrix. This sketch must be
uploaded to the board before using ``board/clock.py`` or ``board/wifi_monitor.py``.

Upload via the GUI's **Live** dropdown ("RPC Frame Receiver") or manually::

    arduino-cli compile --fqbn arduino:zephyr:unoq rpc_receiver
    arduino-cli upload -p /dev/cu.usbmodem19087929472 --fqbn arduino:zephyr:unoq rpc_receiver

Digital Clock (``board/clock.py``)
----------------------------------

A digital clock that runs on the board's Linux side and renders NTP-accurate
time on the LED matrix via Bridge RPC.

- Renders HH:MM using a 3x5 pixel font
- Blinking colon separator (toggles every second)
- Pushes frames every 0.5 seconds

Requires the RPC Frame Receiver sketch. Push and run via ADB::

    adb push board/clock.py /tmp/clock.py
    adb shell "nohup python3 /tmp/clock.py &"

WiFi Scanner (``wifi_scan.py``)
-------------------------------

A standalone tool that scans WiFi networks via ADB and displays signal strength
on the LED matrix.

Usage::

    python wifi_scan.py

This script:

1. Connects to the board's Linux side via ADB
2. Runs a WiFi scan using ``nmcli``
3. Generates an Arduino sketch that displays the results on the LED matrix
4. Compiles and uploads via ``arduino-cli``

WiFi Monitor (``board/wifi_monitor.py``)
----------------------------------------

A persistent WiFi signal monitor that runs on the board's Linux side and
communicates with the Arduino sketch via Bridge RPC (MessagePack protocol).

This tool pushes pre-computed LED frames representing WiFi signal strength
directly to the running sketch. Requires the RPC Frame Receiver sketch.
