#!/usr/bin/env python3
"""GPS Map Display — simulated walking mode.

Same as gps_map.py but ignores GPS and walks a circular path around a
starting point, updating the TFT map every few seconds.  Useful for
testing map rendering without a GPS fix.

Requires: pip3 install Pillow
"""

import concurrent.futures
import io
import math
import os
import socket
import struct
import threading
import time
import urllib.request

ROUTER_SOCK = "/var/run/arduino-router.sock"
TFT_W, TFT_H = 240, 135
IMG_W, IMG_H = 240, 135
ZOOM = 17
TILE_SIZE = 256
TILE_CACHE_DIR = "/tmp/tile_cache"

# Simulated walk parameters
SIM_CENTER_LAT = 38.8573
SIM_CENTER_LON = -77.3822
SIM_RADIUS = 0.002       # ~220m radius
SIM_STEP_DEG = 15        # degrees per step (24 steps = full circle)
SIM_INTERVAL = 5         # seconds between steps


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
    elif isinstance(obj, bytes):
        l = len(obj)
        if l <= 0xff: return b'\xc4' + struct.pack('B', l) + obj
        elif l <= 0xffff: return b'\xc5' + struct.pack('>H', l) + obj
        else: return b'\xc6' + struct.pack('>I', l) + obj
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
        if b == 0xdb:
            d, pos = self._read(pos, 4); l = struct.unpack('>I', d)[0]
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
        self.sock = None; self.next_msgid = 0
        self.lock = threading.Lock()
        self.pending = {}; self.pending_lock = threading.Lock()

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
        self.next_msgid += 1; return self.next_msgid

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
                if isinstance(msg, list) and len(msg) >= 4 and msg[0] == 1:
                    _, msgid, error, result = msg
                    with self.pending_lock:
                        cb = self.pending.pop(msgid, None)
                    if cb:
                        event, result_box = cb
                        result_box[0] = result; result_box[1] = error
                        event.set()


def latlon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x_tile = (lon + 180) / 360 * n
    lat_rad = math.radians(lat)
    y_tile = (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n
    return x_tile, y_tile


def fetch_esri_tile(tx, ty, zoom):
    os.makedirs(TILE_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(TILE_CACHE_DIR, f"{zoom}_{tx}_{ty}.jpg")
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            return f.read()
    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{ty}/{tx}"
    req = urllib.request.Request(url, headers={"User-Agent": "UNO-Q-GPS/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    with open(cache_path, 'wb') as f:
        f.write(data)
    return data


def fetch_map_image(lat, lon, zoom):
    from PIL import Image

    x_float, y_float = latlon_to_tile(lat, lon, zoom)
    tx_center = int(x_float)
    ty_center = int(y_float)
    px_in_tile = int((x_float - tx_center) * TILE_SIZE)
    py_in_tile = int((y_float - ty_center) * TILE_SIZE)

    tile_coords = [(tx_center + dx, ty_center + dy, dx, dy)
                   for dy in range(-1, 2) for dx in range(-1, 2)]
    tiles = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:
        futures = {pool.submit(fetch_esri_tile, tx, ty, zoom): (tx, ty, dx, dy)
                   for tx, ty, dx, dy in tile_coords}
        for fut in concurrent.futures.as_completed(futures):
            tx, ty, dx, dy = futures[fut]
            try:
                tiles[(dx, dy)] = fut.result()
            except Exception as e:
                print(f"  Tile ({tx},{ty}) failed: {e}")

    big = Image.new("RGB", (TILE_SIZE * 3, TILE_SIZE * 3))
    for (dx, dy), data in tiles.items():
        tile = Image.open(io.BytesIO(data))
        big.paste(tile, ((dx + 1) * TILE_SIZE, (dy + 1) * TILE_SIZE))

    cx = TILE_SIZE + px_in_tile
    cy = TILE_SIZE + py_in_tile
    left = cx - TFT_W // 2
    top = cy - TFT_H // 2
    return big.crop((left, top, left + TFT_W, top + TFT_H))


def image_to_rgb565_raw(img):
    rows = []
    for y in range(img.height):
        raw = bytearray(img.width * 2)
        for x in range(img.width):
            r, g, b = img.getpixel((x, y))
            rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            raw[x * 2] = rgb565 >> 8
            raw[x * 2 + 1] = rgb565 & 0xFF
        rows.append(raw)
    return rows


def push_image(bridge, raw_rows):
    for y, raw in enumerate(raw_rows):
        bridge.call("set_row", y, bytes(raw), timeout=5)
        if y % 20 == 0:
            print(f"  Row {y}/{len(raw_rows)}...", flush=True)


def main():
    print("GPS Map Display — Simulated Walk")
    print("=" * 40)
    print(f"TFT: {TFT_W}x{TFT_H}, Zoom: {ZOOM}")
    print(f"Center: {SIM_CENTER_LAT:.4f}, {SIM_CENTER_LON:.4f}")
    print(f"Radius: {SIM_RADIUS} (~{SIM_RADIUS * 111000:.0f}m), Step: {SIM_STEP_DEG} deg")
    print(f"Interval: {SIM_INTERVAL}s")
    print()

    try:
        from PIL import Image  # noqa: F401
        print("Pillow: OK")
    except ImportError:
        print("Pillow not found. Installing...")
        import subprocess
        subprocess.check_call(["pip3", "install", "Pillow"])
        print("Pillow installed.")

    bridge = SimpleBridge()
    bridge.connect()
    time.sleep(2)
    print("Bridge connected.\n")

    bridge.call("clear", "", timeout=5)
    time.sleep(0.5)

    step = 0
    while True:
        try:
            angle = math.radians(step * SIM_STEP_DEG)
            lat = SIM_CENTER_LAT + SIM_RADIUS * math.sin(angle)
            lon = SIM_CENTER_LON + SIM_RADIUS * math.cos(angle)
            step += 1

            print(f"Step {step}: {lat:.6f}, {lon:.6f} ({step * SIM_STEP_DEG % 360} deg)")

            print("  Fetching tiles...")
            try:
                img = fetch_map_image(lat, lon, ZOOM)
            except Exception as e:
                print(f"  Fetch failed: {e}")
                time.sleep(5)
                continue

            print("  Converting...")
            raw_rows = image_to_rgb565_raw(img)

            print("  Pushing...")
            push_image(bridge, raw_rows)
            print("  Done!")

            time.sleep(SIM_INTERVAL)

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
