WiFi Tools
==========

WiFi Scanner (``wifi_scan.py``)
-------------------------------

A standalone tool that scans WiFi networks via ADB and displays signal strength
on the LED matrix.

Usage::

    python wifi_scan.py

This script:

1. Connects to the board's Linux side via ADB
2. Runs a WiFi scan using ``iw``
3. Generates an Arduino sketch that displays the results on the LED matrix
4. Compiles and uploads via ``arduino-cli``

WiFi Monitor (``board/wifi_monitor.py``)
----------------------------------------

A persistent WiFi signal monitor that runs on the board's Linux side and
communicates with the Arduino sketch via Bridge RPC (MessagePack protocol).

This tool pushes pre-computed LED frames representing WiFi signal strength
directly to the running sketch.
