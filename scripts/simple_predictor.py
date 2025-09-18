#!/usr/bin/env python3
#
# scripts/simple_predictor.py
#
# A basic, rule-based prediction engine that consumes the unified event
# stream and attempts to forecast the next likely UI state change.
#
# SETUP INSTRUCTIONS:
# This script launches the unified_event_streamer.py and has the same
# system dependencies. Please see that file for setup instructions.
# It must be run in a graphical X11 session.

import subprocess
import sys
import json
import time

class SimplePredictor:
    def __init__(self):
        self.ui_state = {
            "focused_app": None,
            "focused_element": {
                "name": None,
                "role": None,
            },
            "last_damage_rects": None,
        }
        self.predictions = []

    def update_state(self, event):
        """Updates the internal UI state based on an incoming event."""
        self.predictions = [] # Clear old predictions

        if event.get("source_stream") == "AX":
            if event.get("event_type") == "focus_changed":
                self.ui_state["focused_app"] = event.get("app")
                element = event.get("element", {})
                self.ui_state["focused_element"]["name"] = element.get("name")
                self.ui_state["focused_element"]["role"] = element.get("role")
                self.make_predictions_from_focus(element)

        elif event.get("source_stream") == "DAMAGE":
            self.ui_state["last_damage_rects"] = event.get("dirty_regions")
            self.make_predictions_from_damage(event.get("dirty_regions"))

    def make_predictions_from_focus(self, element):
        """Makes predictions based on a focus change event."""
        name = element.get("name", "").lower()
        role = element.get("role", "").lower()

        if "menu" in role and "file" in name:
            self.predictions.append({
                "type": "focus_change",
                "prediction": "User might click 'Open', 'Save', or 'Exit'.",
                "confidence": 0.7
            })

        if "text" in role or "entry" in role:
            self.predictions.append({
                "type": "text_change",
                "prediction": "User is likely to type text into the focused field.",
                "confidence": 0.8
            })

    def make_predictions_from_damage(self, regions):
        """Makes predictions based on a screen damage event."""
        # Simple prediction: if a small area changes, it might be a button highlight.
        if len(regions) == 1:
            region = regions[0]
            if region["width"] < 100 and region["height"] < 50:
                self.predictions.append({
                    "type": "visual_feedback",
                    "prediction": "A small UI element (like a button) was likely highlighted or clicked.",
                    "confidence": 0.6
                })

    def process_event(self, event):
        """Processes a single event and prints state and predictions."""
        print("\n" + "="*50)
        print(f"EVENT RECEIVED ({event.get('source_stream')} at {event.get('timestamp'):.2f}):")
        print(json.dumps(event, indent=2))

        self.update_state(event)

        print("\nCURRENT UI STATE:")
        print(json.dumps(self.ui_state, indent=2))

        if self.predictions:
            print("\nPREDICTIONS:")
            print(json.dumps(self.predictions, indent=2))
        print("="*50)


def main():
    print("Starting Simple Predictor...")

    try:
        streamer_process = subprocess.Popen(
            [sys.executable, "scripts/unified_event_streamer.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
    except FileNotFoundError:
        print("Error: scripts/unified_event_streamer.py not found.", file=sys.stderr)
        sys.exit(1)

    predictor = SimplePredictor()

    print("Reading from unified event stream...")

    try:
        for line in iter(streamer_process.stdout.readline, ''):
            try:
                event = json.loads(line)
                predictor.process_event(event)
            except json.JSONDecodeError:
                # Ignore non-json lines, which might be status messages
                # from the subprocesses.
                pass

            if streamer_process.poll() is not None:
                print("\nEvent streamer process has terminated.", file=sys.stderr)
                break

    except KeyboardInterrupt:
        print("\nStopping Simple Predictor.")
    finally:
        streamer_process.terminate()
        streamer_process.wait()
        print("Streamer subprocess terminated.")

if __name__ == "__main__":
    main()
