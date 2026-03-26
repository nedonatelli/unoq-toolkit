#!/usr/bin/env python3
"""Weather display via Bridge RPC — fetches Open-Meteo data and pushes to TFT.

Runs on the UNO Q's Linux side. Fetches current weather for Washington, D.C.
and sends it to the MCU for display on the ST7789 TFT.
"""

import json
import socket
import struct
import threading
import time
import urllib.request

ROUTER_SOCK = "/var/run/arduino-router.sock"

# Washington, D.C.
LAT = 38.9072
LON = -77.0369

# Open-Meteo API (free, no key needed)
WEATHER_URL = (
    f"https://api.open-meteo.com/v1/forecast?"
    f"latitude={LAT}&longitude={LON}"
    f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
    f"&daily=temperature_2m_max,temperature_2m_min"
    f"&temperature_unit=fahrenheit&wind_speed_unit=mph"
    f"&timezone=America%2FNew_York&forecast_days=1"
)

# WMO weather code descriptions
WMO_CODES = {
    0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    85: "Light snow shwr", 86: "Heavy snow shwr",
    95: "Thunderstorm", 96: "T-storm w/ hail", 99: "Heavy t-storm",
}


def mp_pack(obj):
    if obj is None: return b'\xc0'
    elif isinstance(obj, bool): return b'\xc3' if obj else b'\xc2'
    elif isinstance(obj, int):
        if 0 <= obj <= 0x7f: return struct.pack('B', obj)
        elif -32 <= obj < 0: return struct.pack('b', obj)
        elif 0 <= obj <= 0xff: return b'\xcc' + struct.pack('B', obj)
        elif 0 <= obj <= 0xffff: return b'\xcd' + struct.pack('>H', obj)
        elif 0 <= obj <= 0xffffffff: return b'\xce' + struct.pack('>I', obj)
        elif -128 <= obj < 0: return b'\xd0' + struct.pack('b', obj)
        elif -32768 <= obj < 0: return b'\xd1' + struct.pack('>h', obj)
        elif -2147483648 <= obj < 0: return b'\xd2' + struct.pack('>i', obj)
        else: return b'\xcf' + struct.pack('>Q', obj)
    elif isinstance(obj, str):
        raw = obj.encode('utf-8'); l = len(raw)
        if l <= 31: return struct.pack('B', 0xa0 | l) + raw
        elif l <= 0xff: return b'\xd9' + struct.pack('B', l) + raw
        elif l <= 0xffff: return b'\xda' + struct.pack('>H', l) + raw
        else: return b'\xdb' + struct.pack('>I', l) + raw
    elif isinstance(obj, (list, tuple)):
        l = len(obj)
        if l <= 15: header = struct.pack('B', 0x90 | l)
        elif l <= 0xffff: header = b'\xdc' + struct.pack('>H', l)
        else: header = b'\xdd' + struct.pack('>I', l)
        return header + b''.join(mp_pack(item) for item in obj)
    elif isinstance(obj, float): return b'\xcb' + struct.pack('>d', obj)
    else: raise TypeError(f"Cannot pack {type(obj)}")


class MsgPackUnpacker:
    def __init__(self):
        self.buf = bytearray(); self.pos = 0
    def feed(self, data): self.buf.extend(data)
    def __iter__(self): return self
    def __next__(self):
        if self.pos >= len(self.buf):
            self.buf = bytearray(); self.pos = 0; raise StopIteration
        try:
            result, new_pos = self._unpack(self.pos); self.pos = new_pos; return result
        except (IndexError, struct.error):
            self.buf = self.buf[self.pos:]; self.pos = 0; raise StopIteration
    def _read(self, pos, n):
        if pos + n > len(self.buf): raise IndexError
        return self.buf[pos:pos+n], pos + n
    def _unpack(self, pos):
        b = self.buf[pos]; pos += 1
        if b <= 0x7f: return b, pos
        if 0x80 <= b <= 0x8f: return self._unpack_map(b & 0x0f, pos)
        if 0x90 <= b <= 0x9f: return self._unpack_array(b & 0x0f, pos)
        if 0xa0 <= b <= 0xbf:
            l = b & 0x1f; data, pos = self._read(pos, l)
            return bytes(data).decode('utf-8'), pos
        if b == 0xc0: return None, pos
        if b == 0xc2: return False, pos
        if b == 0xc3: return True, pos
        if b == 0xcc: v = self.buf[pos]; return v, pos+1
        if b == 0xcd: d, pos = self._read(pos, 2); return struct.unpack('>H', d)[0], pos
        if b == 0xce: d, pos = self._read(pos, 4); return struct.unpack('>I', d)[0], pos
        if b == 0xcf: d, pos = self._read(pos, 8); return struct.unpack('>Q', d)[0], pos
        if b == 0xd0: d, pos = self._read(pos, 1); return struct.unpack('b', d)[0], pos
        if b == 0xd1: d, pos = self._read(pos, 2); return struct.unpack('>h', d)[0], pos
        if b == 0xd2: d, pos = self._read(pos, 4); return struct.unpack('>i', d)[0], pos
        if b == 0xd9:
            l = self.buf[pos]; pos += 1; d, pos = self._read(pos, l)
            return bytes(d).decode('utf-8'), pos
        if b == 0xda:
            d, pos = self._read(pos, 2); l = struct.unpack('>H', d)[0]
            d, pos = self._read(pos, l); return bytes(d).decode('utf-8'), pos
        if b == 0xdc:
            d, pos = self._read(pos, 2); l = struct.unpack('>H', d)[0]
            return self._unpack_array(l, pos)
        if b >= 0xe0: return struct.unpack('b', bytes([b]))[0], pos
        raise ValueError(f"Unknown msgpack byte: 0x{b:02x}")
    def _unpack_array(self, count, pos):
        items = []
        for _ in range(count): item, pos = self._unpack(pos); items.append(item)
        return items, pos
    def _unpack_map(self, count, pos):
        d = {}
        for _ in range(count):
            key, pos = self._unpack(pos); val, pos = self._unpack(pos); d[key] = val
        return d, pos


class SimpleBridge:
    def __init__(self):
        self.sock = None
        self.next_msgid = 0
        self.lock = threading.Lock()
        self.pending = {}
        self.pending_lock = threading.Lock()

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(ROUTER_SOCK)
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

    def call(self, method, *params, timeout=10):
        msgid = self._next_id()
        request = [0, msgid, method, list(params)]
        event = threading.Event()
        result_box = [None, None]
        with self.pending_lock:
            self.pending[msgid] = (event, result_box)
        self._send(request)
        if event.wait(timeout=timeout):
            return result_box[0]
        return None

    def _next_id(self):
        self.next_msgid += 1
        return self.next_msgid

    def _send(self, msg):
        with self.lock:
            self.sock.sendall(mp_pack(msg))

    def _read_loop(self):
        unpacker = MsgPackUnpacker()
        while True:
            data = self.sock.recv(4096)
            if not data: break
            unpacker.feed(data)
            for msg in unpacker:
                if isinstance(msg, list) and len(msg) >= 1:
                    if msg[0] == 1:
                        _, msgid, error, result = msg
                        with self.pending_lock:
                            cb = self.pending.pop(msgid, None)
                        if cb:
                            event, result_box = cb
                            result_box[0] = result
                            result_box[1] = error
                            event.set()


def fetch_weather():
    """Fetch weather from Open-Meteo. Returns CSV string."""
    resp = urllib.request.urlopen(WEATHER_URL, timeout=10)
    data = json.loads(resp.read())

    cur = data["current"]
    daily = data["daily"]

    temp = int(round(cur["temperature_2m"]))
    humidity = int(cur["relative_humidity_2m"])
    wind = int(round(cur["wind_speed_10m"]))
    code = cur["weather_code"]
    high = int(round(daily["temperature_2m_max"][0]))
    low = int(round(daily["temperature_2m_min"][0]))
    desc = WMO_CODES.get(code, f"Code {code}")

    return f"{temp},{high},{low},{humidity},{wind},{code},{desc}"


def main():
    print("TFT Weather Display via Bridge RPC")
    print("=" * 40)

    bridge = SimpleBridge()
    bridge.connect()
    time.sleep(2)
    print("Connected.\n")

    try:
        while True:
            try:
                csv = fetch_weather()
                print(f"  Weather: {csv}")
                bridge.call("set_weather", csv)
            except Exception as e:
                print(f"  Error: {e}")
            # Update every 5 minutes
            time.sleep(300)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()