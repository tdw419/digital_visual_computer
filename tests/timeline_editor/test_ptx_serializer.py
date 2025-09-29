import pytest
from pathlib import Path
from timeline_editor.data_model import Timeline, Layer, Keyframe
from timeline_editor.ptx_serializer import save_timeline, load_timeline

class TestPtxSerializer:
    @pytest.fixture
    def sample_timeline(self):
        timeline = Timeline(width=1024, height=768)
        bg_layer = Layer(name="background")
        bg_layer.add_keyframe(Keyframe(time=0.0, properties={"type": "background", "color": [50, 50, 200]}))
        timeline.add_layer(bg_layer)
        return timeline

    def test_save_and_load_roundtrip(self, sample_timeline, tmp_path):
        filepath = tmp_path / "test.ptx"

        # Save the timeline
        save_timeline(sample_timeline, str(filepath))

        # Check if the file was created
        assert filepath.exists()

        # Load the timeline back
        loaded_timeline = load_timeline(str(filepath))

        # Compare the original and loaded timelines
        assert isinstance(loaded_timeline, Timeline)
        assert loaded_timeline.width == sample_timeline.width
        assert loaded_timeline.height == sample_timeline.height
        assert len(loaded_timeline.layers) == len(sample_timeline.layers)

        original_layer = sample_timeline.layers[0]
        loaded_layer = loaded_timeline.layers[0]
        assert loaded_layer.name == original_layer.name
        assert len(loaded_layer.keyframes) == len(original_layer.keyframes)

        original_kf = original_layer.keyframes[0]
        loaded_kf = loaded_layer.keyframes[0]
        assert loaded_kf.time == original_kf.time
        assert loaded_kf.properties == original_kf.properties