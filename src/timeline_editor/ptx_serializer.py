from __future__ import annotations
import cbor2
from dataclasses import asdict
from .data_model import Timeline, Layer, Keyframe

def save_timeline(timeline: Timeline, filepath: str):
    """Saves a timeline to a PTX file using CBOR."""
    data_to_save = asdict(timeline)
    with open(filepath, "wb") as f:
        cbor2.dump(data_to_save, f)

def load_timeline(filepath: str) -> Timeline:
    """Loads a timeline from a PTX file."""
    with open(filepath, "rb") as f:
        data = cbor2.load(f)

    layers = []
    for layer_data in data.get("layers", []):
        keyframes = []
        for kf_data in layer_data.get("keyframes", []):
            keyframes.append(Keyframe(**kf_data))

        layer_data["keyframes"] = keyframes
        layers.append(Layer(**layer_data))

    data["layers"] = layers
    return Timeline(**data)