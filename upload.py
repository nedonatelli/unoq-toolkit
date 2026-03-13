#!/usr/bin/env python3
"""Sketch launcher — list, compile, and upload .ino sketches to the Arduino UNO Q."""

import glob, os, subprocess, sys

FQBN = "arduino:zephyr:unoq"
PORT = "/dev/cu.usbmodem19087929472"
SKIP = {"blink"}  # auto-generated scratch directory

def find_sketches():
    base = os.path.dirname(os.path.abspath(__file__))
    sketches = []
    for ino in sorted(glob.glob(os.path.join(base, "*", "*.ino"))):
        name = os.path.basename(os.path.dirname(ino))
        if name not in SKIP:
            sketches.append((name, os.path.dirname(ino)))
    return sketches

def main():
    sketches = find_sketches()
    if not sketches:
        print("No sketches found."); return

    print("\nAvailable sketches:")
    print("-" * 40)
    for i, (name, _) in enumerate(sketches, 1):
        print(f"  {i}. {name}")
    print()

    try:
        choice = input("Select sketch number (or q to quit): ").strip()
    except (KeyboardInterrupt, EOFError):
        print(); return

    if choice.lower() == 'q':
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(sketches):
            raise ValueError
    except ValueError:
        print("Invalid selection."); return

    name, path = sketches[idx]
    print(f"\nCompiling {name}...")
    r = subprocess.run(["arduino-cli", "compile", "--fqbn", FQBN, path])
    if r.returncode != 0:
        print("Compile failed."); return

    print(f"\nUploading {name}...")
    r = subprocess.run(["arduino-cli", "upload", "-p", PORT, "--fqbn", FQBN, path])
    if r.returncode != 0:
        print("Upload failed."); return

    print(f"\n{name} uploaded successfully!")

if __name__ == "__main__":
    main()
