from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Keyframe:
    """Represents a single keyframe in the timeline."""
    time: float  # Time in seconds
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Layer:
    """Represents a layer in the timeline, containing multiple keyframes."""
    name: str
    keyframes: List[Keyframe] = field(default_factory=list)

    def add_keyframe(self, keyframe: Keyframe):
        """Adds a keyframe and keeps them sorted by time."""
        self.keyframes.append(keyframe)
        self.keyframes.sort(key=lambda kf: kf.time)

@dataclass
class Timeline:
    """Represents the entire timeline, including all layers and settings."""
    width: int = 800
    height: int = 600
    layers: List[Layer] = field(default_factory=list)

    def add_layer(self, layer: Layer):
        """Adds a layer to the timeline."""
        self.layers.append(layer)

    def get_layer(self, name: str) -> Layer | None:
        """Finds a layer by its name."""
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None