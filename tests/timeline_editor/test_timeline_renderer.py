import pytest
import numpy as np
from timeline_editor.data_model import Timeline, Layer, Keyframe
from timeline_editor.timeline_renderer import TimelineRenderer

class TestTimelineRenderer:
    def test_render_background_color(self):
        timeline = Timeline(width=100, height=100)
        bg_layer = Layer(name="background")
        bg_layer.add_keyframe(Keyframe(time=0.0, properties={"type": "background", "color": [255, 0, 0]}))
        timeline.add_layer(bg_layer)

        renderer = TimelineRenderer(timeline)
        frame = renderer.render_frame(0.0)

        assert frame.shape == (100, 100, 3)
        assert np.all(frame[0, 0] == [255, 0, 0])

    def test_interpolation(self):
        timeline = Timeline(width=100, height=100)
        layer = Layer(name="test")
        layer.add_keyframe(Keyframe(time=0.0, properties={"x": 0, "color": [0, 0, 0]}))
        layer.add_keyframe(Keyframe(time=10.0, properties={"x": 100, "color": [255, 255, 255]}))
        timeline.add_layer(layer)

        from timeline_editor.timeline_renderer import _get_interpolated_properties

        # Test interpolation at midpoint
        props = _get_interpolated_properties(layer, 5.0)
        assert props["x"] == 50
        assert props["color"] == [127.5, 127.5, 127.5]

        # Test before start
        props = _get_interpolated_properties(layer, -1.0)
        assert props["x"] == 0

        # Test after end
        props = _get_interpolated_properties(layer, 11.0)
        assert props["x"] == 100

    def test_render_text_layer(self):
        timeline = Timeline(width=200, height=100)
        text_layer = Layer(name="title")
        text_layer.add_keyframe(Keyframe(time=0.0, properties={
            "type": "text", "text": "Hi", "x": 10, "y": 10, "size": 30, "color": [255, 255, 255]
        }))
        timeline.add_layer(text_layer)

        renderer = TimelineRenderer(timeline)
        frame = renderer.render_frame(0.0)

        # A simple check to see if pixels were drawn.
        # A more robust test would involve image comparison.
        assert frame.shape == (100, 200, 3)
        assert np.sum(frame) > 0 # Check that the frame is not all black

    def test_warp_and_shadow(self):
        timeline = Timeline(width=300, height=400)

        shadow_layer = Layer(name="card_shadow")
        shadow_layer.add_keyframe(Keyframe(time=0.0, properties={
            "type": "shadow", "target_layer": "card", "radius": 5, "strength": 0.5, "offset": [5, 5]
        }))
        timeline.add_layer(shadow_layer)

        card_layer = Layer(name="card")
        card_layer.add_keyframe(Keyframe(time=0.0, properties={
            "type": "warp", "size": [100, 150], "color": [200, 200, 250],
            "quad": [[80, 40], [180, 60], [160, 240], [60, 220]]
        }))
        timeline.add_layer(card_layer)

        renderer = TimelineRenderer(timeline)
        frame = renderer.render_frame(0.0)

        assert frame.shape == (400, 300, 3)
        assert np.sum(frame) > 0

        # Check if some pixels are dark (shadow)
        assert np.any(frame < 50)
        # Check if some pixels are bright (card)
        assert np.any(frame > 150)