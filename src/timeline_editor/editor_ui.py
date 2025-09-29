from __future__ import annotations
import pygame
import numpy as np
from .data_model import Timeline, Layer, Keyframe
from .timeline_renderer import TimelineRenderer
from .ptx_serializer import save_timeline, load_timeline

class TimelineEditorUI:
    """Manages the UI for the timeline editor."""

    def __init__(self, timeline: Timeline):
        pygame.init()
        self.timeline = timeline
        self.screen = pygame.display.set_mode((timeline.width, timeline.height))
        pygame.display.set_caption("Timeline Editor")
        self.clock = pygame.time.Clock()
        self.running = True
        self.playing = False
        self.current_time = 0.0  # in seconds
        self.max_time = 10.0  # Total duration of the timeline in seconds
        self.renderer = TimelineRenderer(timeline)
        self.viewport_surface = pygame.Surface((timeline.width - 100, timeline.height - 200))

    def run(self):
        """The main loop of the editor."""
        while self.running:
            delta_time = self.clock.tick(60) / 1000.0

            self._handle_events()

            if self.playing:
                self.current_time += delta_time
                if self.current_time > self.max_time:
                    self.current_time = 0.0

            self._render()
            self._draw()

        pygame.quit()

    def _handle_events(self):
        """Handles user input and other events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.playing = not self.playing

                # Save and Load
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL:
                    if event.key == pygame.K_s:
                        self._save_timeline()
                    elif event.key == pygame.K_o:
                        self._load_timeline()

    def _save_timeline(self):
        try:
            save_timeline(self.timeline, "timeline.ptx")
            print("Timeline saved to timeline.ptx")
        except Exception as e:
            print(f"Error saving timeline: {e}")

    def _load_timeline(self):
        try:
            self.timeline = load_timeline("timeline.ptx")
            self.renderer = TimelineRenderer(self.timeline) # Re-init renderer with new timeline
            print("Timeline loaded from timeline.ptx")
        except Exception as e:
            print(f"Error loading timeline: {e}")

    def _render(self):
        """Renders the current frame of the timeline."""
        frame = self.renderer.render_frame(self.current_time)
        # The VM returns a (H, W, C) array, but pygame needs (W, H, C)
        # and surfarray works best with transposed axes.
        frame_transposed = np.transpose(frame, (1, 0, 2))
        pygame.surfarray.blit_array(self.viewport_surface, frame_transposed)


    def _draw(self):
        """Draws all the UI elements."""
        self.screen.fill((20, 20, 20))

        # Viewport
        viewport_rect = self.viewport_surface.get_rect(topleft=(50, 50))
        self.screen.blit(self.viewport_surface, viewport_rect)

        # Timeline scrubber
        timeline_rect = pygame.Rect(50, self.timeline.height - 100, self.timeline.width - 100, 50)
        pygame.draw.rect(self.screen, (60, 60, 60), timeline_rect)

        # Scrubber handle
        if self.max_time > 0:
            progress = self.current_time / self.max_time
            handle_x = timeline_rect.x + progress * timeline_rect.width
            handle_x = max(timeline_rect.x, min(handle_x, timeline_rect.right))
            handle_rect = pygame.Rect(handle_x - 2, timeline_rect.y, 4, timeline_rect.height)
            pygame.draw.rect(self.screen, (255, 100, 100), handle_rect)

        pygame.display.flip()

def main():
    """Entry point for the timeline editor application."""
    timeline = Timeline(width=1024, height=768)

    # Background layer
    bg_layer = Layer(name="background")
    bg_layer.add_keyframe(Keyframe(time=0.0, properties={"type": "background", "color": [50, 50, 200]}))
    bg_layer.add_keyframe(Keyframe(time=5.0, properties={"type": "background", "color": [50, 200, 50]}))
    bg_layer.add_keyframe(Keyframe(time=10.0, properties={"type": "background", "color": [50, 50, 200]}))
    timeline.add_layer(bg_layer)

    # Shadow for the card
    shadow_layer = Layer(name="card_shadow")
    shadow_layer.add_keyframe(Keyframe(time=0.0, properties={
        "type": "shadow", "target_layer": "card", "radius": 8, "strength": 0.7, "offset": [10, 12]
    }))
    timeline.add_layer(shadow_layer)

    # A warping card layer
    card_layer = Layer(name="card")
    card_layer.add_keyframe(Keyframe(time=0.0, properties={
        "type": "warp", "size": [200, 300], "color": [200, 200, 250],
        "quad": [[80, 40], [280, 60], [260, 340], [60, 320]]
    }))
    card_layer.add_keyframe(Keyframe(time=2.5, properties={
        "type": "warp", "size": [200, 300], "color": [250, 200, 200],
        "quad": [[180, 40], [180, 60], [160, 340], [160, 320]] # Squeezed
    }))
    card_layer.add_keyframe(Keyframe(time=5.0, properties={
        "type": "warp", "size": [200, 300], "color": [200, 250, 200],
        "quad": [[80, 40], [280, 60], [260, 340], [60, 320]]
    }))
    card_layer.add_keyframe(Keyframe(time=10.0, properties={
        "type": "warp", "size": [200, 300], "color": [200, 200, 250],
        "quad": [[180, 40], [380, 60], [360, 340], [160, 320]]
    }))
    timeline.add_layer(card_layer)

    # Text layer on top
    text_layer = Layer(name="title")
    text_layer.add_keyframe(Keyframe(time=0.0, properties={
        "type": "text", "text": "Hello, World!", "x": 50, "y": 300, "size": 48, "color": [255, 255, 255]
    }))
    text_layer.add_keyframe(Keyframe(time=10.0, properties={
        "type": "text", "text": "Hello, World!", "x": 500, "y": 300, "size": 48, "color": [255, 255, 100]
    }))
    timeline.add_layer(text_layer)

    editor = TimelineEditorUI(timeline)
    editor.run()

if __name__ == "__main__":
    main()