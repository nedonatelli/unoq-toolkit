#!/usr/bin/env python3
"""Interactive GUI to design and upload patterns/animations to Arduino UNO Q LED Matrix (13x8)"""

import tkinter as tk
import subprocess
import threading
import copy
import os

ROWS = 8
COLS = 13
LED_SIZE = 40
PAD = 2

# --- Pre-canned shapes (8 rows x 13 cols, 1=on 0=off) ---
SHAPES = {
    "Heart": [
        [0,0,0,1,1,0,0,0,1,1,0,0,0],
        [0,0,1,1,1,1,0,1,1,1,1,0,0],
        [0,1,1,1,1,1,1,1,1,1,1,1,0],
        [0,1,1,1,1,1,1,1,1,1,1,1,0],
        [0,0,1,1,1,1,1,1,1,1,1,0,0],
        [0,0,0,1,1,1,1,1,1,1,0,0,0],
        [0,0,0,0,1,1,1,1,1,0,0,0,0],
        [0,0,0,0,0,1,1,1,0,0,0,0,0],
    ],
    "Smiley": [
        [0,0,0,0,1,1,1,1,1,0,0,0,0],
        [0,0,0,1,0,0,0,0,0,1,0,0,0],
        [0,0,1,0,0,1,0,1,0,0,1,0,0],
        [0,0,1,0,0,0,0,0,0,0,1,0,0],
        [0,0,1,0,1,0,0,0,1,0,1,0,0],
        [0,0,1,0,0,1,1,1,0,0,1,0,0],
        [0,0,0,1,0,0,0,0,0,1,0,0,0],
        [0,0,0,0,1,1,1,1,1,0,0,0,0],
    ],
    "Star": [
        [0,0,0,0,0,0,1,0,0,0,0,0,0],
        [0,0,0,0,0,1,1,1,0,0,0,0,0],
        [0,1,1,1,1,1,1,1,1,1,1,1,0],
        [0,0,1,1,1,1,1,1,1,1,1,0,0],
        [0,0,0,1,1,1,1,1,1,1,0,0,0],
        [0,0,1,1,1,0,0,0,1,1,1,0,0],
        [0,1,1,1,0,0,0,0,0,1,1,1,0],
        [0,1,0,0,0,0,0,0,0,0,0,1,0],
    ],
    "Arrow Up": [
        [0,0,0,0,0,0,1,0,0,0,0,0,0],
        [0,0,0,0,0,1,1,1,0,0,0,0,0],
        [0,0,0,0,1,1,1,1,1,0,0,0,0],
        [0,0,0,1,1,1,1,1,1,1,0,0,0],
        [0,0,0,0,0,1,1,1,0,0,0,0,0],
        [0,0,0,0,0,1,1,1,0,0,0,0,0],
        [0,0,0,0,0,1,1,1,0,0,0,0,0],
        [0,0,0,0,0,1,1,1,0,0,0,0,0],
    ],
    "Arrow Right": [
        [0,0,0,0,0,0,1,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,1,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,1,0,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,0,0,0],
        [0,0,0,0,0,0,0,0,1,0,0,0,0],
        [0,0,0,0,0,0,0,1,0,0,0,0,0],
        [0,0,0,0,0,0,1,0,0,0,0,0,0],
    ],
    "Check": [
        [0,0,0,0,0,0,0,0,0,0,0,1,0],
        [0,0,0,0,0,0,0,0,0,0,1,1,0],
        [0,0,0,0,0,0,0,0,0,1,1,0,0],
        [0,0,0,0,0,0,0,0,1,1,0,0,0],
        [0,1,0,0,0,0,0,1,1,0,0,0,0],
        [0,1,1,0,0,0,1,1,0,0,0,0,0],
        [0,0,1,1,0,1,1,0,0,0,0,0,0],
        [0,0,0,1,1,1,0,0,0,0,0,0,0],
    ],
    "X Mark": [
        [0,1,1,0,0,0,0,0,0,0,1,1,0],
        [0,0,1,1,0,0,0,0,0,1,1,0,0],
        [0,0,0,1,1,0,0,0,1,1,0,0,0],
        [0,0,0,0,1,1,0,1,1,0,0,0,0],
        [0,0,0,0,1,1,0,1,1,0,0,0,0],
        [0,0,0,1,1,0,0,0,1,1,0,0,0],
        [0,0,1,1,0,0,0,0,0,1,1,0,0],
        [0,1,1,0,0,0,0,0,0,0,1,1,0],
    ],
    "Diamond": [
        [0,0,0,0,0,0,1,0,0,0,0,0,0],
        [0,0,0,0,0,1,0,1,0,0,0,0,0],
        [0,0,0,0,1,0,0,0,1,0,0,0,0],
        [0,0,0,1,0,0,0,0,0,1,0,0,0],
        [0,0,0,1,0,0,0,0,0,1,0,0,0],
        [0,0,0,0,1,0,0,0,1,0,0,0,0],
        [0,0,0,0,0,1,0,1,0,0,0,0,0],
        [0,0,0,0,0,0,1,0,0,0,0,0,0],
    ],
    "Music Note": [
        [0,0,0,0,0,0,1,1,1,1,0,0,0],
        [0,0,0,0,0,0,1,0,0,1,0,0,0],
        [0,0,0,0,0,0,1,0,0,1,0,0,0],
        [0,0,0,0,0,0,1,0,0,1,0,0,0],
        [0,0,0,0,0,0,1,0,0,1,0,0,0],
        [0,0,0,1,1,1,1,0,0,1,0,0,0],
        [0,0,1,1,1,1,1,0,1,1,1,0,0],
        [0,0,0,1,1,1,0,0,0,1,1,0,0],
    ],
    "Skull": [
        [0,0,0,1,1,1,1,1,1,1,0,0,0],
        [0,0,1,1,1,1,1,1,1,1,1,0,0],
        [0,0,1,0,0,1,1,1,0,0,1,0,0],
        [0,0,1,0,0,1,1,1,0,0,1,0,0],
        [0,0,1,1,1,1,0,1,1,1,1,0,0],
        [0,0,0,1,1,0,1,0,1,1,0,0,0],
        [0,0,0,1,0,1,0,1,0,1,0,0,0],
        [0,0,0,0,1,0,1,0,1,0,0,0,0],
    ],
}

# --- Pre-canned animations (list of (shape_data, duration_ms)) ---
def _make_frames(data_list):
    return [([[bool(cell) for cell in row] for row in frame], dur) for frame, dur in data_list]

ANIMATIONS = {}

# Heartbeat
ANIMATIONS["Heartbeat"] = lambda: _make_frames([
    (SHAPES["Heart"], 400),
    ([[False]*COLS for _ in range(ROWS)], 100),
    (SHAPES["Heart"], 200),
    ([[False]*COLS for _ in range(ROWS)], 600),
])

# Rain
def _rain_frames():
    import random
    random.seed(42)
    frames = []
    frames = []
    positions = {}  # col -> list of row positions
    random.seed(42)
    for f in range(10):
        grid = [[False]*COLS for _ in range(ROWS)]
        # Add new drops at top
        if f % 2 == 0:
            for _ in range(3):
                c = random.randint(0, COLS - 1)
                if c not in positions:
                    positions[c] = []
                positions[c].append(0)
        # Draw and advance drops
        new_positions = {}
        for c, rows in positions.items():
            new_rows = []
            for r in rows:
                if r < ROWS:
                    grid[r][c] = True
                    new_rows.append(r + 1)
            if new_rows:
                new_positions[c] = new_rows
        positions = new_positions
        frames.append(([row[:] for row in grid], 150))
    return _make_frames([(f, d) for f, d in frames])

ANIMATIONS["Rain"] = _rain_frames

# Wave
def _wave_frames():
    import math
    frames = []
    for phase in range(8):
        grid = [[False]*COLS for _ in range(ROWS)]
        for c in range(COLS):
            h = int(3 + 2.5 * math.sin(2 * math.pi * (c / COLS + phase / 8)))
            for r in range(ROWS - h, ROWS):
                grid[r][c] = True
        frames.append((grid, 120))
    return _make_frames([(f, d) for f, d in frames])

ANIMATIONS["Wave"] = _wave_frames

# Expanding diamond
def _expand_frames():
    frames = []
    cx, cy = 6, 3.5
    for size in range(1, 7):
        grid = [[False]*COLS for _ in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLS):
                if abs(c - cx) + abs(r - cy) <= size and abs(c - cx) + abs(r - cy) >= size - 1:
                    grid[r][c] = True
        frames.append((grid, 150))
    # Contract back
    for size in range(5, 0, -1):
        grid = [[False]*COLS for _ in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLS):
                if abs(c - cx) + abs(r - cy) <= size and abs(c - cx) + abs(r - cy) >= size - 1:
                    grid[r][c] = True
        frames.append((grid, 150))
    return _make_frames([(f, d) for f, d in frames])

ANIMATIONS["Pulse"] = _expand_frames

# Scrolling marquee
def _scroll_frames():
    # Create a wide "HI" pattern and scroll it across
    text_pattern = [
        [1,0,1,0,1,1,0],
        [1,0,1,0,0,1,0],
        [1,1,1,0,0,1,0],
        [1,0,1,0,0,1,0],
        [1,0,1,0,1,1,1],
    ]
    text_h = len(text_pattern)
    text_w = len(text_pattern[0])
    total_w = COLS + text_w
    frames = []
    for offset in range(total_w):
        grid = [[False]*COLS for _ in range(ROWS)]
        y_off = (ROWS - text_h) // 2
        for tr in range(text_h):
            for tc in range(text_w):
                col = COLS - offset + tc
                if 0 <= col < COLS and text_pattern[tr][tc]:
                    grid[y_off + tr][col] = True
        frames.append((grid, 120))
    return _make_frames([(f, d) for f, d in frames])

ANIMATIONS["Scroll HI"] = _scroll_frames

# Snake
def _snake_frames():
    # Snake that moves around the border
    border_cells = []
    for c in range(COLS): border_cells.append((0, c))
    for r in range(1, ROWS): border_cells.append((r, COLS-1))
    for c in range(COLS-2, -1, -1): border_cells.append((ROWS-1, c))
    for r in range(ROWS-2, 0, -1): border_cells.append((r, 0))
    length = 6
    frames = []
    for start in range(0, len(border_cells), 2):
        grid = [[False]*COLS for _ in range(ROWS)]
        for i in range(length):
            idx = (start + i) % len(border_cells)
            r, c = border_cells[idx]
            grid[r][c] = True
        frames.append((grid, 80))
    return _make_frames([(f, d) for f, d in frames])

ANIMATIONS["Snake"] = _snake_frames

# Fireworks
def _firework_frames():
    frames = []
    cx, cy = 6, 4
    # Rise
    for y in range(ROWS-1, cy, -1):
        grid = [[False]*COLS for _ in range(ROWS)]
        grid[y][cx] = True
        frames.append((grid, 100))
    # Explode
    for radius in range(1, 5):
        grid = [[False]*COLS for _ in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLS):
                d = ((r - cy)**2 + (c - cx)**2) ** 0.5
                if abs(d - radius) < 1.0:
                    grid[r][c] = True
        frames.append((grid, 120))
    # Fade
    frames.append(([[False]*COLS for _ in range(ROWS)], 300))
    return _make_frames([(f, d) for f, d in frames])

ANIMATIONS["Firework"] = _firework_frames

# --- Live sketches (generative code that runs on-board) ---
# Each returns a complete .ino sketch string
LIVE_SKETCHES = {
    "ADC Noise Random": '''\
// ADC noise-seeded random LED matrix
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;
uint32_t frame[4];

uint32_t adcNoiseSeed() {
  uint32_t seed = 0;
  for (int i = 0; i < 32; i++) {
    seed = (seed << 1) | (analogRead(A0) & 1);
  }
  return seed;
}

void setup() {
  matrix.begin();
  randomSeed(adcNoiseSeed());
}

void loop() {
  // Re-seed periodically from ADC noise for fresh entropy
  randomSeed(adcNoiseSeed());

  for (int i = 0; i < 4; i++) {
    frame[i] = 0;
    for (int b = 0; b < 32; b++) {
      if (random(2)) {
        frame[i] |= (1UL << (31 - b));
      }
    }
  }
  // Mask off unused bits (only 104 of 128 bits matter)
  frame[3] &= 0xFF000000;

  matrix.loadFrame(frame);
  delay(100);
}
''',
    "ADC Noise Rain": '''\
// ADC noise-seeded rain effect
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;
uint8_t grid[8][13] = {0};

uint32_t adcNoiseSeed() {
  uint32_t seed = 0;
  for (int i = 0; i < 32; i++) {
    seed = (seed << 1) | (analogRead(A0) & 1);
  }
  return seed;
}

void gridToFrame(uint32_t* frame) {
  frame[0] = frame[1] = frame[2] = frame[3] = 0;
  for (int r = 0; r < 8; r++) {
    for (int c = 0; c < 13; c++) {
      int bit = r * 13 + c;
      if (grid[r][c]) {
        frame[bit / 32] |= (1UL << (31 - (bit % 32)));
      }
    }
  }
}

void setup() {
  matrix.begin();
  randomSeed(adcNoiseSeed());
}

void loop() {
  // Shift all rows down
  for (int r = 7; r > 0; r--) {
    for (int c = 0; c < 13; c++) {
      grid[r][c] = grid[r-1][c];
    }
  }
  // Clear top row and add new random drops
  for (int c = 0; c < 13; c++) {
    grid[0][c] = 0;
  }
  // Re-seed from ADC noise and spawn 1-3 drops
  randomSeed(adcNoiseSeed());
  int nDrops = random(1, 4);
  for (int i = 0; i < nDrops; i++) {
    grid[0][random(13)] = 1;
  }

  uint32_t frame[4];
  gridToFrame(frame);
  matrix.loadFrame(frame);
  delay(120);
}
''',
    "ADC Noise Life": '''\
// ADC noise-seeded Game of Life
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;
uint8_t grid[8][13] = {0};
uint8_t next_grid[8][13] = {0};
int generation = 0;

uint32_t adcNoiseSeed() {
  uint32_t seed = 0;
  for (int i = 0; i < 32; i++) {
    seed = (seed << 1) | (analogRead(A0) & 1);
  }
  return seed;
}

void gridToFrame(uint32_t* frame) {
  frame[0] = frame[1] = frame[2] = frame[3] = 0;
  for (int r = 0; r < 8; r++) {
    for (int c = 0; c < 13; c++) {
      int bit = r * 13 + c;
      if (grid[r][c]) {
        frame[bit / 32] |= (1UL << (31 - (bit % 32)));
      }
    }
  }
}

void randomize() {
  randomSeed(adcNoiseSeed());
  for (int r = 0; r < 8; r++)
    for (int c = 0; c < 13; c++)
      grid[r][c] = random(2);
  generation = 0;
}

int countNeighbors(int r, int c) {
  int count = 0;
  for (int dr = -1; dr <= 1; dr++) {
    for (int dc = -1; dc <= 1; dc++) {
      if (dr == 0 && dc == 0) continue;
      int nr = (r + dr + 8) % 8;
      int nc = (c + dc + 13) % 13;
      count += grid[nr][nc];
    }
  }
  return count;
}

void step() {
  for (int r = 0; r < 8; r++) {
    for (int c = 0; c < 13; c++) {
      int n = countNeighbors(r, c);
      if (grid[r][c])
        next_grid[r][c] = (n == 2 || n == 3) ? 1 : 0;
      else
        next_grid[r][c] = (n == 3) ? 1 : 0;
    }
  }
  memcpy(grid, next_grid, sizeof(grid));
  generation++;
}

void setup() {
  matrix.begin();
  randomize();
}

void loop() {
  uint32_t frame[4];
  gridToFrame(frame);
  matrix.loadFrame(frame);
  delay(200);
  step();
  // Re-randomize if stagnant (every 100 generations)
  if (generation >= 100) {
    randomize();
  }
}
''',
    "Bouncing Square": '''\
// ADC noise-seeded bouncing 2x2 square
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;

int x, y;
int dx, dy;

uint32_t adcNoiseSeed() {
  uint32_t seed = 0;
  for (int i = 0; i < 32; i++) {
    seed = (seed << 1) | (analogRead(A0) & 1);
  }
  return seed;
}

void gridToFrame(uint8_t grid[8][13], uint32_t* frame) {
  frame[0] = frame[1] = frame[2] = frame[3] = 0;
  for (int r = 0; r < 8; r++) {
    for (int c = 0; c < 13; c++) {
      int bit = r * 13 + c;
      if (grid[r][c]) {
        frame[bit / 32] |= (1UL << (31 - (bit % 32)));
      }
    }
  }
}

void setup() {
  matrix.begin();
  randomSeed(adcNoiseSeed());

  // Random starting position (within bounds for 2x2)
  x = random(0, 12);  // 0..11 so x+1 <= 12
  y = random(0, 7);   // 0..6 so y+1 <= 7

  // Random velocity: -1 or +1 for each axis
  dx = random(2) ? 1 : -1;
  dy = random(2) ? 1 : -1;
}

void loop() {
  uint8_t grid[8][13] = {0};

  // Draw 2x2 square
  grid[y][x] = 1;
  grid[y][x+1] = 1;
  grid[y+1][x] = 1;
  grid[y+1][x+1] = 1;

  uint32_t frame[4];
  gridToFrame(grid, frame);
  matrix.loadFrame(frame);

  // Move
  x += dx;
  y += dy;

  // Bounce off edges
  if (x <= 0 || x >= 11) dx = -dx;
  if (y <= 0 || y >= 6) dy = -dy;

  // Clamp just in case
  if (x < 0) x = 0;
  if (x > 11) x = 11;
  if (y < 0) y = 0;
  if (y > 6) y = 6;

  delay(80);
}
''',
}
PORT = "/dev/cu.usbmodem19087929472"
FQBN = "arduino:zephyr:unoq"
SKETCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blink")

COLOR_ON = "#00ff44"
COLOR_OFF = "#222222"


def empty_frame():
    return [[False] * COLS for _ in range(ROWS)]


def copy_frame(frame):
    return copy.deepcopy(frame)


def state_to_uint32s(state):
    """Convert 8x13 bool grid to 4x uint32_t frame data."""
    bits = []
    for r in range(ROWS):
        for c in range(COLS):
            bits.append(1 if state[r][c] else 0)
    frame = [0, 0, 0, 0]
    for i in range(104):
        if bits[i]:
            frame[i // 32] |= (1 << (31 - (i % 32)))
    return frame


class CanvasButton:
    """A button drawn on a canvas for reliable color control on macOS."""

    def __init__(self, parent, text, command, bg="#333333", fg="white",
                 width=80, height=32, font=("Helvetica", 11)):
        self.command = command
        self.bg = bg
        self.fg = fg
        self.width = width
        self.height = height
        self.font = font
        self.text = text

        self.canvas = tk.Canvas(parent, width=width, height=height,
                                bg=parent["bg"], highlightthickness=0)
        self.rect = self.canvas.create_rectangle(
            0, 0, width, height, fill=bg, outline="#555555", width=1
        )
        self.label = self.canvas.create_text(
            width // 2, height // 2, text=text, fill=fg, font=font
        )
        self.canvas.bind("<Button-1>", lambda e: self.command())
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)

    def _on_enter(self, e):
        # Lighten the background slightly on hover
        self.canvas.itemconfig(self.rect, outline="#888888")

    def _on_leave(self, e):
        self.canvas.itemconfig(self.rect, outline="#555555")

    def config(self, **kwargs):
        if "bg" in kwargs:
            self.bg = kwargs["bg"]
            self.canvas.itemconfig(self.rect, fill=self.bg)
        if "text" in kwargs:
            self.text = kwargs["text"]
            self.canvas.itemconfig(self.label, text=self.text)
        if "fg" in kwargs:
            self.fg = kwargs["fg"]
            self.canvas.itemconfig(self.label, fill=self.fg)


class LEDMatrixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("UNO Q LED Matrix Animator")
        self.root.configure(bg="#111111")
        self.uploading = False
        self.previewing = False
        self.preview_job = None

        # Animation: list of (frame_state, duration_ms)
        self.frames = [(empty_frame(), 200)]
        self.current_frame_idx = 0

        self.dragging = False
        self.drag_value = True
        self.timeline_dragging = False
        self.timeline_drag_idx = None

        # --- Canvas ---
        canvas_w = COLS * (LED_SIZE + PAD) + PAD
        canvas_h = ROWS * (LED_SIZE + PAD) + PAD
        self.canvas = tk.Canvas(
            root, width=canvas_w, height=canvas_h, bg="#111111", highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=10)

        self.rects = [[None] * COLS for _ in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLS):
                x1 = PAD + c * (LED_SIZE + PAD)
                y1 = PAD + r * (LED_SIZE + PAD)
                x2 = x1 + LED_SIZE
                y2 = y1 + LED_SIZE
                rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=COLOR_OFF, outline="#333333", width=1
                )
                self.rects[r][c] = rect

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # --- Draw tools ---
        draw_frame = tk.Frame(root, bg="#111111")
        draw_frame.pack(pady=(0, 5))
        for text, cmd in [("All On", self.all_on), ("All Off", self.all_off), ("Invert", self.invert)]:
            btn = CanvasButton(draw_frame, text, cmd, bg="#333333", fg="white", width=70, height=28,
                               font=("Helvetica", 11))
            btn.pack(side=tk.LEFT, padx=4)

        # --- Presets ---
        preset_frame = tk.Frame(root, bg="#111111")
        preset_frame.pack(pady=(5, 5))

        tk.Label(preset_frame, text="Shapes:", bg="#111111", fg="#888888",
                 font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(0, 4))
        self.shape_var = tk.StringVar(value="Heart")
        shape_menu = tk.OptionMenu(preset_frame, self.shape_var, *SHAPES.keys())
        shape_menu.config(bg="#333333", fg="white", highlightthickness=0,
                          activebackground="#444444", activeforeground="white",
                          font=("Helvetica", 10), width=10)
        shape_menu["menu"].config(bg="#333333", fg="white",
                                   activebackground="#555555", activeforeground="white")
        shape_menu.pack(side=tk.LEFT, padx=2)
        CanvasButton(preset_frame, "Load", self.load_shape, bg="#444444", fg="white",
                     width=50, height=28, font=("Helvetica", 10)).pack(side=tk.LEFT, padx=2)

        tk.Label(preset_frame, text="  Animations:", bg="#111111", fg="#888888",
                 font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(8, 4))
        self.anim_var = tk.StringVar(value="Heartbeat")
        anim_menu = tk.OptionMenu(preset_frame, self.anim_var, *ANIMATIONS.keys())
        anim_menu.config(bg="#333333", fg="white", highlightthickness=0,
                         activebackground="#444444", activeforeground="white",
                         font=("Helvetica", 10), width=10)
        anim_menu["menu"].config(bg="#333333", fg="white",
                                  activebackground="#555555", activeforeground="white")
        anim_menu.pack(side=tk.LEFT, padx=2)
        CanvasButton(preset_frame, "Load", self.load_animation, bg="#444444", fg="white",
                     width=50, height=28, font=("Helvetica", 10)).pack(side=tk.LEFT, padx=2)

        # --- Live Sketches ---
        live_frame = tk.Frame(root, bg="#111111")
        live_frame.pack(pady=(0, 5))

        tk.Label(live_frame, text="Live (on-board):", bg="#111111", fg="#888888",
                 font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(0, 4))
        self.live_var = tk.StringVar(value=list(LIVE_SKETCHES.keys())[0])
        live_menu = tk.OptionMenu(live_frame, self.live_var, *LIVE_SKETCHES.keys())
        live_menu.config(bg="#333333", fg="white", highlightthickness=0,
                         activebackground="#444444", activeforeground="white",
                         font=("Helvetica", 10), width=16)
        live_menu["menu"].config(bg="#333333", fg="white",
                                  activebackground="#555555", activeforeground="white")
        live_menu.pack(side=tk.LEFT, padx=2)
        CanvasButton(live_frame, "Upload", self.upload_live, bg="#664400", fg="white",
                     width=60, height=28, font=("Helvetica", 10)).pack(side=tk.LEFT, padx=2)

        # --- Timeline ---
        tk.Label(root, text="FRAMES", bg="#111111", fg="#888888",
                 font=("Helvetica", 10, "bold")).pack(pady=(10, 2))

        timeline_outer = tk.Frame(root, bg="#111111")
        timeline_outer.pack(pady=(0, 5), fill=tk.X, padx=10)

        # Scrollable timeline
        timeline_scroll_w = canvas_w - 60  # leave room for buttons

        timeline_scroll_container = tk.Frame(timeline_outer, bg="#111111")
        timeline_scroll_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.timeline_canvas = tk.Canvas(timeline_scroll_container, height=70, width=timeline_scroll_w,
                                         bg="#111111", highlightthickness=0)
        self.timeline_canvas.pack(fill=tk.X, expand=True)

        self.timeline_scrollbar = tk.Scrollbar(timeline_scroll_container, orient=tk.HORIZONTAL,
                                                command=self.timeline_canvas.xview)
        self.timeline_scrollbar.pack(fill=tk.X)
        self.timeline_canvas.configure(xscrollcommand=self.timeline_scrollbar.set)

        self.timeline_frame = tk.Frame(self.timeline_canvas, bg="#111111")
        self.timeline_window = self.timeline_canvas.create_window(
            (0, 0), window=self.timeline_frame, anchor="nw"
        )
        self.timeline_frame.bind("<Configure>", self._on_timeline_configure)
        self.timeline_canvas.bind("<MouseWheel>", self._on_timeline_scroll)
        self.timeline_canvas.bind("<Shift-MouseWheel>", self._on_timeline_scroll)

        btn_col = tk.Frame(timeline_outer, bg="#111111")
        btn_col.pack(side=tk.RIGHT, padx=(10, 0))

        CanvasButton(btn_col, "+", self.add_frame, bg="#336633", fg="white",
                     width=40, height=24, font=("Helvetica", 12)).pack(pady=1)
        CanvasButton(btn_col, "Dup", self.dup_frame, bg="#335533", fg="white",
                     width=40, height=24, font=("Helvetica", 10)).pack(pady=1)
        CanvasButton(btn_col, "-", self.del_frame, bg="#663333", fg="white",
                     width=40, height=24, font=("Helvetica", 12)).pack(pady=1)

        # --- Duration ---
        dur_frame = tk.Frame(root, bg="#111111")
        dur_frame.pack(pady=(0, 5))
        tk.Label(dur_frame, text="Frame duration (ms):", bg="#111111", fg="#aaaaaa").pack(side=tk.LEFT)
        self.dur_var = tk.StringVar(value="200")
        self.dur_entry = tk.Entry(dur_frame, textvariable=self.dur_var, width=6, bg="#222222", fg="white",
                                  insertbackground="white")
        self.dur_entry.pack(side=tk.LEFT, padx=4)
        self.dur_entry.bind("<FocusOut>", self.on_dur_change)
        self.dur_entry.bind("<Return>", self.on_dur_change)

        # --- Preview / Upload ---
        action_frame = tk.Frame(root, bg="#111111")
        action_frame.pack(pady=(5, 5))

        self.preview_btn = CanvasButton(
            action_frame, "Preview", self.toggle_preview,
            bg="#555500", fg="white", width=120, height=40, font=("Helvetica", 14)
        )
        self.preview_btn.pack(side=tk.LEFT, padx=6)

        self.upload_btn = CanvasButton(
            action_frame, "Upload", self.upload,
            bg="#0066cc", fg="white", width=120, height=40, font=("Helvetica", 14)
        )
        self.upload_btn.pack(side=tk.LEFT, padx=6)

        # --- Status ---
        self.status_var = tk.StringVar(value="Design frames, then Upload")
        tk.Label(root, textvariable=self.status_var, bg="#111111", fg="#888888",
                 font=("Helvetica", 11)).pack(pady=(0, 10))

        self.rebuild_timeline()
        self.load_frame_to_canvas(0)

    # --- Drawing ---

    def get_cell(self, event):
        c = (event.x - PAD) // (LED_SIZE + PAD)
        r = (event.y - PAD) // (LED_SIZE + PAD)
        if 0 <= r < ROWS and 0 <= c < COLS:
            return r, c
        return None, None

    def on_press(self, event):
        if self.previewing:
            return
        r, c = self.get_cell(event)
        if r is not None:
            self.dragging = True
            state = self.frames[self.current_frame_idx][0]
            self.drag_value = not state[r][c]
            state[r][c] = self.drag_value
            self.update_cell(r, c)
            self.rebuild_timeline()

    def on_drag(self, event):
        if not self.dragging or self.previewing:
            return
        r, c = self.get_cell(event)
        if r is not None:
            state = self.frames[self.current_frame_idx][0]
            if state[r][c] != self.drag_value:
                state[r][c] = self.drag_value
                self.update_cell(r, c)
                self.rebuild_timeline()

    def on_release(self, event):
        self.dragging = False

    def update_cell(self, r, c):
        state = self.frames[self.current_frame_idx][0]
        color = COLOR_ON if state[r][c] else COLOR_OFF
        self.canvas.itemconfig(self.rects[r][c], fill=color)

    def update_all_cells(self):
        state = self.frames[self.current_frame_idx][0]
        for r in range(ROWS):
            for c in range(COLS):
                color = COLOR_ON if state[r][c] else COLOR_OFF
                self.canvas.itemconfig(self.rects[r][c], fill=color)

    def upload_live(self):
        if self.uploading:
            return
        if self.previewing:
            self.stop_preview()
        name = self.live_var.get()
        sketch_code = LIVE_SKETCHES[name]
        self.uploading = True
        self.upload_btn.config(bg="#666633", text="Uploading...")
        self.status_var.set(f"Compiling live sketch: {name}...")

        def do_upload():
            try:
                sketch_path = os.path.join(SKETCH_DIR, "blink.ino")
                with open(sketch_path, "w") as f:
                    f.write(sketch_code)
                result = subprocess.run(
                    ["arduino-cli", "compile", "--fqbn", FQBN, SKETCH_DIR],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode != 0:
                    self.root.after(0, lambda: self.upload_done(False, f"Compile error:\n{result.stderr}"))
                    return
                self.root.after(0, lambda: self.status_var.set("Uploading to board..."))
                result = subprocess.run(
                    ["arduino-cli", "upload", "-p", PORT, "--fqbn", FQBN, SKETCH_DIR],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode != 0:
                    self.root.after(0, lambda: self.upload_done(False, f"Upload error:\n{result.stderr}"))
                    return
                self.root.after(0, lambda: self.upload_done(True, f"Live sketch '{name}' uploaded!"))
            except Exception as e:
                self.root.after(0, lambda: self.upload_done(False, str(e)))

        threading.Thread(target=do_upload, daemon=True).start()

    def load_shape(self):
        name = self.shape_var.get()
        shape = SHAPES[name]
        state = [[bool(cell) for cell in row] for row in shape]
        self.frames[self.current_frame_idx] = (state, self.frames[self.current_frame_idx][1])
        self.update_all_cells()
        self.rebuild_timeline()

    def load_animation(self):
        name = self.anim_var.get()
        self.frames = ANIMATIONS[name]()
        self.current_frame_idx = 0
        self.load_frame_to_canvas(0)

    def all_on(self):
        self.frames[self.current_frame_idx] = ([[True] * COLS for _ in range(ROWS)],
                                                 self.frames[self.current_frame_idx][1])
        self.update_all_cells()
        self.rebuild_timeline()

    def all_off(self):
        self.frames[self.current_frame_idx] = (empty_frame(), self.frames[self.current_frame_idx][1])
        self.update_all_cells()
        self.rebuild_timeline()

    def invert(self):
        state = self.frames[self.current_frame_idx][0]
        for r in range(ROWS):
            for c in range(COLS):
                state[r][c] = not state[r][c]
        self.update_all_cells()
        self.rebuild_timeline()

    # --- Frame management ---

    def load_frame_to_canvas(self, idx):
        self.current_frame_idx = idx
        self.update_all_cells()
        dur = self.frames[idx][1]
        self.dur_var.set(str(dur))
        self.rebuild_timeline()

    def add_frame(self):
        self.frames.insert(self.current_frame_idx + 1, (empty_frame(), 200))
        self.load_frame_to_canvas(self.current_frame_idx + 1)

    def dup_frame(self):
        cur = self.frames[self.current_frame_idx]
        self.frames.insert(self.current_frame_idx + 1, (copy_frame(cur[0]), cur[1]))
        self.load_frame_to_canvas(self.current_frame_idx + 1)

    def del_frame(self):
        if len(self.frames) <= 1:
            return
        del self.frames[self.current_frame_idx]
        new_idx = min(self.current_frame_idx, len(self.frames) - 1)
        self.load_frame_to_canvas(new_idx)

    def on_dur_change(self, event=None):
        try:
            dur = int(self.dur_var.get())
            dur = max(10, dur)
        except ValueError:
            dur = 200
        self.dur_var.set(str(dur))
        state = self.frames[self.current_frame_idx][0]
        self.frames[self.current_frame_idx] = (state, dur)

    def rebuild_timeline(self):
        for widget in self.timeline_frame.winfo_children():
            widget.destroy()

        thumb_size = 6
        for i, (state, dur) in enumerate(self.frames):
            frame_container = tk.Frame(self.timeline_frame, bg="#111111")
            frame_container.pack(side=tk.LEFT, padx=2)

            border_color = "#00ff44" if i == self.current_frame_idx else "#333333"
            border = tk.Frame(frame_container, bg=border_color, padx=2, pady=2)
            border.pack()

            thumb = tk.Canvas(border, width=COLS * thumb_size, height=ROWS * thumb_size,
                              bg="#111111", highlightthickness=0)
            thumb.pack()
            for r in range(ROWS):
                for c in range(COLS):
                    color = "#00ff44" if state[r][c] else "#1a1a1a"
                    thumb.create_rectangle(
                        c * thumb_size, r * thumb_size,
                        (c + 1) * thumb_size, (r + 1) * thumb_size,
                        fill=color, outline=""
                    )
            thumb.bind("<ButtonPress-1>", lambda e, idx=i: self._timeline_press(idx))
            thumb.bind("<B1-Motion>", lambda e, idx=i: self._timeline_drag(e, idx))
            thumb.bind("<ButtonRelease-1>", lambda e: self._timeline_release())

            tk.Label(frame_container, text=f"{dur}ms", bg="#111111", fg="#666666",
                     font=("Helvetica", 9)).pack()

        # Scroll to show the current frame
        self.timeline_frame.update_idletasks()
        self._on_timeline_configure()

    def _timeline_press(self, idx):
        self.timeline_dragging = False
        self.timeline_drag_idx = idx

    def _timeline_drag(self, event, source_idx):
        if self.timeline_drag_idx is None:
            return
        self.timeline_dragging = True
        # Find which frame index the mouse is over
        children = self.timeline_frame.winfo_children()
        mouse_x = event.x_root
        for i, child in enumerate(children):
            cx = child.winfo_rootx()
            cw = child.winfo_width()
            if cx <= mouse_x < cx + cw:
                if i != self.timeline_drag_idx:
                    # Swap frames
                    frames = self.frames
                    frame = frames.pop(self.timeline_drag_idx)
                    frames.insert(i, frame)
                    # Update current_frame_idx to follow the selected frame
                    if self.current_frame_idx == self.timeline_drag_idx:
                        self.current_frame_idx = i
                    elif self.timeline_drag_idx < self.current_frame_idx <= i:
                        self.current_frame_idx -= 1
                    elif i <= self.current_frame_idx < self.timeline_drag_idx:
                        self.current_frame_idx += 1
                    self.timeline_drag_idx = i
                    self.rebuild_timeline()
                break

    def _timeline_release(self):
        if not self.timeline_dragging and self.timeline_drag_idx is not None:
            # It was a click, not a drag — select the frame
            self.load_frame_to_canvas(self.timeline_drag_idx)
        self.timeline_dragging = False
        self.timeline_drag_idx = None

    def _on_timeline_configure(self, event=None):
        self.timeline_canvas.configure(scrollregion=self.timeline_canvas.bbox("all"))

    def _on_timeline_scroll(self, event):
        self.timeline_canvas.xview_scroll(-1 if event.delta > 0 else 1, "units")

    # --- Preview ---

    def toggle_preview(self):
        if self.previewing:
            self.stop_preview()
        else:
            self.start_preview()

    def start_preview(self):
        self.previewing = True
        self.preview_btn.config(text="Stop", bg="#aa5500")
        self.preview_frame_idx = 0
        self.show_preview_frame()

    def stop_preview(self):
        self.previewing = False
        self.preview_btn.config(text="Preview", bg="#555500")
        if self.preview_job:
            self.root.after_cancel(self.preview_job)
            self.preview_job = None
        self.load_frame_to_canvas(self.current_frame_idx)

    def show_preview_frame(self):
        if not self.previewing:
            return
        idx = self.preview_frame_idx
        state, dur = self.frames[idx]
        for r in range(ROWS):
            for c in range(COLS):
                color = COLOR_ON if state[r][c] else COLOR_OFF
                self.canvas.itemconfig(self.rects[r][c], fill=color)
        self.status_var.set(f"Preview: frame {idx + 1}/{len(self.frames)}")
        self.preview_frame_idx = (idx + 1) % len(self.frames)
        self.preview_job = self.root.after(dur, self.show_preview_frame)

    # --- Upload ---

    def generate_sketch(self):
        if len(self.frames) == 1:
            frame = state_to_uint32s(self.frames[0][0])
            sketch = f"""// Auto-generated LED Matrix pattern
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
        else:
            frame_lines = []
            for state, dur in self.frames:
                f = state_to_uint32s(state)
                frame_lines.append(
                    f"  {{ 0x{f[0]:08X}, 0x{f[1]:08X}, 0x{f[2]:08X}, 0x{f[3]:08X}, {dur} }}"
                )
            frames_str = ",\n".join(frame_lines)

            sketch = f"""// Auto-generated LED Matrix animation
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;

const uint32_t animation[][5] = {{
{frames_str}
}};

void setup() {{
  matrix.begin();
}}

void loop() {{
  matrix.loadSequence(animation);
  matrix.playSequence();
}}
"""
        sketch_path = os.path.join(SKETCH_DIR, "blink.ino")
        with open(sketch_path, "w") as f:
            f.write(sketch)

    def upload(self):
        if self.uploading:
            return
        if self.previewing:
            self.stop_preview()
        self.on_dur_change()
        self.uploading = True
        self.upload_btn.config(bg="#666633", text="Uploading...")
        n = len(self.frames)
        self.status_var.set(f"Compiling {n} frame{'s' if n > 1 else ''}...")

        def do_upload():
            try:
                self.generate_sketch()
                result = subprocess.run(
                    ["arduino-cli", "compile", "--fqbn", FQBN, SKETCH_DIR],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode != 0:
                    self.root.after(0, lambda: self.upload_done(False, f"Compile error:\n{result.stderr}"))
                    return

                self.root.after(0, lambda: self.status_var.set("Uploading to board..."))
                result = subprocess.run(
                    ["arduino-cli", "upload", "-p", PORT, "--fqbn", FQBN, SKETCH_DIR],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode != 0:
                    self.root.after(0, lambda: self.upload_done(False, f"Upload error:\n{result.stderr}"))
                    return

                self.root.after(0, lambda: self.upload_done(True,
                    f"{'Animation' if n > 1 else 'Pattern'} uploaded! ({n} frame{'s' if n > 1 else ''})"))
            except Exception as e:
                self.root.after(0, lambda: self.upload_done(False, str(e)))

        threading.Thread(target=do_upload, daemon=True).start()

    def upload_done(self, success, message):
        self.uploading = False
        if success:
            self.upload_btn.config(bg="#0066cc", text="Upload")
            self.status_var.set(message)
        else:
            self.upload_btn.config(bg="#cc0000", text="Failed")
            self.status_var.set(message[:80])
            self.root.after(3000, lambda: self.upload_btn.config(bg="#0066cc", text="Upload"))

    def on_close(self):
        if self.preview_job:
            self.root.after_cancel(self.preview_job)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = LEDMatrixGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
