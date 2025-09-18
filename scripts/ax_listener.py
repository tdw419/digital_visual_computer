#!/usr/bin/env python3
#
# scripts/ax_listener.py
#
# Listens for accessibility events on Linux using the AT-SPI D-Bus service.
# This script provides a stream of semantic UI events, such as focus changes,
# window creation, and property changes.
#
# SETUP INSTRUCTIONS:
# This script requires system-level dependencies that may not be installed by default
# and cannot be installed via pip alone.
#
# On Debian/Ubuntu, you need to install the following packages:
#   sudo apt-get update
#   sudo apt-get install -y at-spi2-core python3-pyatspi2
#
# On Fedora/CentOS, the packages might be named differently, e.g.:
#   sudo dnf install -y at-spi2-core python3-pyatspi
#
# After installing these system packages, the script should run successfully.

import gi
gi.require_version('Atspi', '2.0')
from gi.repository import Atspi
import json
import time
import sys

def on_focus_change(accessible):
    """Callback for focus change events."""
    try:
        role = Atspi.role_get_name(accessible.get_role())
        name = accessible.get_name()
        app = accessible.get_app()
        app_name = app.get_name() if app else "UnknownApp"

        event_data = {
            "timestamp": time.time(),
            "event_type": "focus_changed",
            "app": app_name,
            "element": {
                "role": role,
                "name": name,
                "path": accessible.get_path()
            }
        }
        print(json.dumps(event_data), flush=True)
    except Exception as e:
        # Sometimes objects become invalid before we can access them
        pass

def on_window_event(event):
    """Callback for window creation/destruction events."""
    try:
        source = event.source
        role = Atspi.role_get_name(source.get_role())
        name = source.get_name()

        event_data = {
            "timestamp": time.time(),
            "event_type": f"window_{event.type}", # e.g., window_opened, window_closed
            "element": {
                "role": role,
                "name": name,
                "path": source.get_path()
            }
        }
        print(json.dumps(event_data), flush=True)
    except Exception as e:
        pass

def main():
    print("Starting Accessibility Tree (AX) Listener...")
    print("Listening for UI events. Press Ctrl+C to exit.")

    try:
        # Initialize the AT-SPI registry
        Atspi.Registry.get_default()

        # Register a listener for focus events on the desktop
        desktop = Atspi.get_desktop(0)
        Atspi.Registry.register_event_listener(on_focus_change, "object:state-changed:focused")

        # Register listeners for window events
        Atspi.Registry.register_event_listener(on_window_event, "window:opened")
        Atspi.Registry.register_event_listener(on_window_event, "window:closed")

        # Start the main event loop
        Atspi.run()

    except gi.repository.GLib.Error as e:
        print(f"Error: Could not connect to the AT-SPI D-Bus service.", file=sys.stderr)
        print(f"Please ensure the at-spi2-core service is running.", file=sys.stderr)
        print(f"You may need to run: /usr/libexec/at-spi-bus-launcher --launch-immediately", file=sys.stderr)
        print(f"Original error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopping AX Listener.")
        Atspi.exit()
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
