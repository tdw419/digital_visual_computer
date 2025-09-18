#!/usr/bin/env python3
#
# scripts/unified_event_streamer.py
#
# Fuses the semantic event stream from the Accessibility Tree (AX) listener
# with the visual change stream from the Screen Damage listener into a single,
# rich, and contextual stream of UI events.
#
# SETUP INSTRUCTIONS:
# This script launches ax_listener.py and damage_listener.py as subprocesses.
# It requires the same system dependencies as those scripts.
#
# On Debian/Ubuntu:
#   sudo apt-get update
#   sudo apt-get install -y at-spi2-core python3-pyatspi2 libx11-dev libxdamage-dev
#
# You will also need python-xlib:
#   pip install python-xlib
#
# This script must be run in a graphical X11 session.

import subprocess
import sys
import threading
import queue
import json
import time

def stream_reader(process, stream_queue, stream_name):
    """Reads lines from a subprocess's stdout and puts them in a queue."""
    for line in iter(process.stdout.readline, ''):
        try:
            # Parse the JSON line and add metadata
            event = json.loads(line)
            event["source_stream"] = stream_name
            stream_queue.put(event)
        except json.JSONDecodeError:
            # Ignore lines that are not valid JSON
            pass
    process.stdout.close()

def main():
    print("Starting Unified Event Streamer...")

    # --- Start the AX Listener Subprocess ---
    try:
        print("Launching AX listener...")
        ax_process = subprocess.Popen(
            [sys.executable, "scripts/ax_listener.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 # Line-buffered
        )
    except FileNotFoundError:
        print("Error: scripts/ax_listener.py not found.", file=sys.stderr)
        sys.exit(1)

    # --- Start the Damage Listener Subprocess ---
    try:
        print("Launching Damage listener...")
        damage_process = subprocess.Popen(
            [sys.executable, "scripts/damage_listener.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 # Line-buffered
        )
    except FileNotFoundError:
        print("Error: scripts/damage_listener.py not found.", file=sys.stderr)
        ax_process.terminate()
        sys.exit(1)

    # --- Setup Queues and Threads for Reading Streams ---
    event_queue = queue.Queue()

    ax_thread = threading.Thread(
        target=stream_reader,
        args=(ax_process, event_queue, "AX")
    )
    damage_thread = threading.Thread(
        target=stream_reader,
        args=(damage_process, event_queue, "DAMAGE")
    )

    ax_thread.daemon = True
    damage_thread.daemon = True

    ax_thread.start()
    damage_thread.start()

    print("\n--- Unified Event Stream ---")
    print("Listening for events from both streams. Press Ctrl+C to exit.")

    try:
        while True:
            # Check for errors from subprocesses
            if ax_process.poll() is not None:
                print("\nAX listener process has terminated.", file=sys.stderr)
                errors = ax_process.stderr.read()
                if errors:
                    print("AX Listener Errors:\n", errors, file=sys.stderr)
                break

            if damage_process.poll() is not None:
                print("\nDamage listener process has terminated.", file=sys.stderr)
                errors = damage_process.stderr.read()
                if errors:
                    print("Damage Listener Errors:\n", errors, file=sys.stderr)
                break

            # Get the next event from the queue
            try:
                event = event_queue.get(timeout=1.0)
                # For now, just print the unified event.
                # A more advanced implementation would correlate these events.
                print(json.dumps(event, indent=2))
            except queue.Empty:
                # No event in the last second, continue listening
                continue

    except KeyboardInterrupt:
        print("\nStopping Unified Event Streamer.")
    finally:
        # Cleanly terminate the subprocesses
        ax_process.terminate()
        damage_process.terminate()
        ax_process.wait()
        damage_process.wait()
        print("Subprocesses terminated.")

if __name__ == "__main__":
    main()
