from __future__ import annotations
from typing import List, Any, Dict
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from .data_model import Timeline, Keyframe, Layer
from .kernels import warp_perspective, soft_shadow

def _lerp(a: float, b: float, t: float) -> float:
    """Linearly interpolates between two values."""
    return a + (b - a) * t

def _interpolate_property(k_start: Keyframe, k_end: Keyframe, prop_name: str, time: float) -> Any:
    """Interpolates a single property between two keyframes."""
    if prop_name not in k_start.properties or prop_name not in k_end.properties:
        return k_start.properties.get(prop_name)

    start_val = k_start.properties[prop_name]
    end_val = k_end.properties[prop_name]

    duration = k_end.time - k_start.time
    if duration == 0:
        return start_val

    t = (time - k_start.time) / duration

    if isinstance(start_val, (int, float)) and isinstance(end_val, (int, float)):
        return _lerp(start_val, end_val, t)

    if isinstance(start_val, (list, tuple)) and isinstance(end_val, (list, tuple)):
        return [_lerp(s, e, t) for s, e in zip(start_val, end_val)]

    return start_val

def _get_interpolated_properties(layer: Layer, time: float) -> dict[str, Any]:
    if not layer.keyframes: return {}
    if time <= layer.keyframes[0].time: return layer.keyframes[0].properties
    if time >= layer.keyframes[-1].time: return layer.keyframes[-1].properties

    for i in range(len(layer.keyframes) - 1):
        if layer.keyframes[i].time <= time < layer.keyframes[i+1].time:
            k_start, k_end = layer.keyframes[i], layer.keyframes[i+1]
            all_prop_names = set(k_start.properties.keys()) | set(k_end.properties.keys())
            return {name: _interpolate_property(k_start, k_end, name, time) for name in all_prop_names}
    return {}

class TimelineRenderer:
    """Renders a timeline by processing layers in order."""

    def __init__(self, timeline: Timeline):
        self.timeline = timeline
        self.font_cache: Dict[int, ImageFont.FreeTypeFont] = {}

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self.font_cache:
            self.font_cache[size] = ImageFont.truetype("assets/Roboto-Regular.ttf", size)
        return self.font_cache[size]

    def render_frame(self, time: float) -> np.ndarray:
        framebuffer = np.zeros((self.timeline.height, self.timeline.width, 3), dtype=np.uint8)
        rendered_layer_cache: Dict[str, np.ndarray] = {}

        for layer in self.timeline.layers:
            props = _get_interpolated_properties(layer, time)
            if not props: continue

            layer_type = props.get("type", "none")

            if layer_type == "background":
                color = tuple(int(c) for c in props.get("color", (0,0,0)))
                framebuffer[:, :] = color

            elif layer_type == "text":
                font = self._get_font(int(props.get("size", 24)))
                color = tuple(int(c) for c in props.get("color", (255,255,255)))
                img_fb = Image.fromarray(framebuffer)
                draw = ImageDraw.Draw(img_fb)
                draw.text((props.get("x", 0), props.get("y", 0)), props.get("text", ""), font=font, fill=color)
                framebuffer = np.array(img_fb)

            elif layer_type == "shadow":
                target_name = props.get("target_layer")
                if target_name in rendered_layer_cache:
                    target_rgba = rendered_layer_cache[target_name]
                    alpha_mask = (target_rgba[:, :, 3] / 255.0).astype(np.float32)
                    shadow_rgb = soft_shadow(
                        alpha_mask,
                        props.get("radius", 6),
                        props.get("offset", (8,8)),
                        props.get("color", (0,0,0)),
                        props.get("strength", 0.6)
                    )
                    # Composite shadow behind existing content
                    img_fb = Image.fromarray(framebuffer)
                    img_shadow = Image.fromarray(shadow_rgb)
                    img_shadow_alpha = Image.fromarray((shadow_rgb.sum(axis=2) > 0) * int(255 * props.get("strength", 0.6))).convert('L')

                    temp_buffer = Image.new('RGB', (self.timeline.width, self.timeline.height))
                    temp_buffer.paste(img_shadow, (0,0))
                    temp_buffer.paste(img_fb, (0,0), img_fb.convert('RGBA'))
                    framebuffer = np.array(temp_buffer)

            elif layer_type == "warp":
                w, h = props.get("size", (200, 300))
                color = tuple(int(c) for c in props.get("color", (200, 200, 250)))
                card_image = np.full((h, w, 4), (*color, 255), dtype=np.uint8) # RGBA

                quad = np.array(props["quad"], dtype=np.float32)
                warped_rgba = warp_perspective(card_image, (self.timeline.height, self.timeline.width), quad)

                img_fb = Image.fromarray(framebuffer)
                img_card = Image.fromarray(warped_rgba, 'RGBA')
                img_fb.paste(img_card, (0, 0), img_card)
                framebuffer = np.array(img_fb)
                rendered_layer_cache[layer.name] = warped_rgba

        return framebuffer