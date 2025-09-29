import pytest
from timeline_editor.data_model import Timeline, Layer, Keyframe

class TestDataModel:
    def test_timeline_creation(self):
        timeline = Timeline(width=1920, height=1080)
        assert timeline.width == 1920
        assert timeline.height == 1080
        assert timeline.layers == []

    def test_layer_creation(self):
        layer = Layer(name="test_layer")
        assert layer.name == "test_layer"
        assert layer.keyframes == []

    def test_keyframe_creation(self):
        keyframe = Keyframe(time=5.0, properties={"x": 100, "y": 200})
        assert keyframe.time == 5.0
        assert keyframe.properties == {"x": 100, "y": 200}

    def test_add_layer_to_timeline(self):
        timeline = Timeline()
        layer = Layer(name="new_layer")
        timeline.add_layer(layer)
        assert len(timeline.layers) == 1
        assert timeline.layers[0].name == "new_layer"

    def test_get_layer_from_timeline(self):
        timeline = Timeline()
        layer1 = Layer(name="layer1")
        layer2 = Layer(name="layer2")
        timeline.add_layer(layer1)
        timeline.add_layer(layer2)

        found_layer = timeline.get_layer("layer2")
        assert found_layer is not None
        assert found_layer.name == "layer2"

        not_found_layer = timeline.get_layer("layer3")
        assert not_found_layer is None

    def test_add_keyframe_to_layer(self):
        layer = Layer(name="test_layer")
        kf1 = Keyframe(time=10.0)
        kf2 = Keyframe(time=0.0)
        kf3 = Keyframe(time=5.0)

        layer.add_keyframe(kf1)
        layer.add_keyframe(kf2)
        layer.add_keyframe(kf3)

        assert len(layer.keyframes) == 3
        assert layer.keyframes[0].time == 0.0
        assert layer.keyframes[1].time == 5.0
        assert layer.keyframes[2].time == 10.0