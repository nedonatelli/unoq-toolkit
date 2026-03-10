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
