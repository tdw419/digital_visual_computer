#!/usr/bin/env python3
#
# scripts/damage_listener.py
#
# Listens for screen damage events on Linux/X11 using the XDamage extension.
# This script provides a low-latency stream of "dirty regions" from the screen.
#
# SETUP INSTRUCTIONS:
# This script requires a running X11 display server. It will not work in a
# headless environment or on Wayland without XWayland.
#
# The `python-xlib` library must be installed:
#   pip install python-xlib
#
# You may also need to install the X11 development libraries on your system:
#   sudo apt-get install -y libx11-dev libxdamage-dev
#

import Xlib
from Xlib import X, display
from Xlib.ext import damage, xfixes
import json
import time
import sys

def main():
    print("Starting Screen Damage Listener (X11)...")

    try:
        # Connect to the X server
        disp = display.Display()
        root = disp.screen().root
    except Xlib.error.DisplayNameError:
        print("Error: Could not connect to X server.", file=sys.stderr)
        print("Please ensure you are running in a graphical X11 session.", file=sys.stderr)
        sys.exit(1)

    # Check for XDamage extension
    if not disp.has_extension("DAMAGE"):
        print("Error: XDamage extension not available on this server.", file=sys.stderr)
        sys.exit(1)

    print("Listening for screen updates. Press Ctrl+C to exit.")

    # Create a Damage object
    damage_id = disp.generate_id()
    damage.Create(disp, damage_id, root, damage.ReportLevel.NonEmpty)

    try:
        while True:
            # Wait for the next event
            evt = disp.next_event()

            # Check if it's a DamageNotify event
            if evt.type == disp.extension_event.DamageNotify:
                if evt.damage == damage_id:
                    # We have a damage event, acknowledge it to get the region
                    region_id = disp.generate_id()
                    damage.Subtract(disp, damage_id, X.NONE, region_id)

                    # Get the rectangles in the damaged region
                    rectangles = xfixes.FetchRegion(disp, region_id).rectangles
                    disp.destroy_region(region_id)

                    if rectangles:
                        event_data = {
                            "timestamp": time.time(),
                            "event_type": "screen_damage",
                            "dirty_regions": [
                                {"x": r.x, "y": r.y, "width": r.width, "height": r.height}
                                for r in rectangles
                            ]
                        }
                        print(json.dumps(event_data), flush=True)

    except KeyboardInterrupt:
        print("\nStopping Damage Listener.")
    finally:
        # Clean up the Damage object
        damage.Destroy(disp, damage_id)
        disp.close()

if __name__ == "__main__":
    main()
