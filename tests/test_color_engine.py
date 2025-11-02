# tests/test_color_engine.py
import unittest
import numpy as np
from color_engine.engine import ColorEngine

class TestColorEngine(unittest.TestCase):

    def setUp(self):
        """Set up a new ColorEngine for each test."""
        self.engine = ColorEngine()

    def test_vector_blend(self):
        """1. Gold Test: Vector Blend"""
        space = self.engine.space
        c1 = '🔵'
        c2 = '🟢'

        # Blend 'blue' and 'green'
        blended_color = space.blend(c1, c2, w=0.5)

        # The nearest color should be one of the original colors or a neighbor
        self.assertIn(blended_color, space.colors)

        # Test extreme weights
        self.assertEqual(space.blend(c1, c2, w=0.0), c2)
        self.assertEqual(space.blend(c1, c2, w=1.0), c1)

    def test_parallel_attention_run(self):
        """2. Gold Test: Parallel Attention Run"""
        grid = [
            ['🔵', '🟡'],
            ['🟢', '🔴']
        ]
        output, attention_weights = self.engine.attn.execute(grid)

        # Output should have the same dimensions as input
        self.assertEqual(len(output), len(grid))
        self.assertEqual(len(output[0]), len(grid[0]))

        # Attention weights should be a square matrix of size (N*M)x(N*M)
        num_cells = len(grid) * len(grid[0])
        self.assertEqual(attention_weights.shape, (num_cells, num_cells))

        # Each row in the attention matrix should sum to 1 (softmax)
        for row in attention_weights:
            self.assertAlmostEqual(np.sum(row), 1.0, places=6)

    def test_pattern_match(self):
        """3. Gold Test: Pattern Match"""
        grid1 = [['🔵']]
        grid2 = [['🟦']]
        grid3 = [['🔴']]

        # Store some patterns
        self.engine.mem.store(grid1, {"note": "blue"})
        self.engine.mem.store(grid2, {"note": "dark_blue"})

        # Search for a similar pattern
        similar_patterns = self.engine.mem.similar(grid1, k=1)

        # The most similar pattern should be grid1 itself
        self.assertEqual(len(similar_patterns), 1)
        self.assertEqual(similar_patterns[0]['grid'], grid1)

        # Search for a pattern that doesn't exist
        similar_to_red = self.engine.mem.similar(grid3, k=1)
        self.assertNotEqual(similar_to_red[0]['grid'], grid3 if similar_to_red else None)

    def test_gradient_mapping(self):
        """4. Gold Test: Gradient Mapping"""
        prob_engine = self.engine.prob
        start_color = '🟢'
        end_color = '🔴'

        # Test midpoint
        mid_color = prob_engine.gradient(start_color, end_color, 0.5)
        self.assertIn(mid_color, self.engine.space.colors)

        # Test endpoints
        self.assertEqual(prob_engine.gradient(start_color, end_color, 0.0), start_color)
        self.assertEqual(prob_engine.gradient(start_color, end_color, 1.0), end_color)

    def test_learn_store_recall(self):
        """5. Gold Test: Learn-Store-Recall Loop"""
        grid = [['🧠', '➡️', '✅']]
        note = "successful thought process"

        # 1. Learn
        self.engine.learn(grid, success=True, note=note)

        # 2. Store (implicit in learn)
        self.assertEqual(len(self.engine.mem.records), 1)

        # 3. Recall
        result = self.engine.think(grid)

        # The top outcome should match what we just learned
        self.assertIsNotNone(result['top_outcome'])
        self.assertTrue(result['top_outcome']['success'])
        self.assertEqual(result['top_outcome']['note'], note)
        self.assertEqual(result['similar_found'], 1)

if __name__ == '__main__':
    unittest.main()
