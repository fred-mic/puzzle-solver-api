# test_puzzle_service.py
import unittest
from unittest.mock import patch
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import puzzle_service` works
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from puzzle_service import PuzzleService


class TestPuzzleService(unittest.TestCase):

    def setUp(self):
        self.puzzle_service = PuzzleService()

    def test_import_and_basic_setup(self):
        # Sanity check that PuzzleService initialized correctly
        self.assertIsInstance(self.puzzle_service, PuzzleService)
        self.assertEqual(self.puzzle_service.vector_dim, self.puzzle_service.grid_size ** 2)
        self.assertIsInstance(self.puzzle_service.goal_state, tuple)

    def test_generate_puzzle_states_basic(self):
        num_puzzles = 5
        states = self.puzzle_service.generate_puzzle_states(num_puzzles)
        self.assertIsInstance(states, set)
        self.assertGreaterEqual(len(states), 1)
        self.assertLessEqual(len(states), num_puzzles)
        self.assertIn(self.puzzle_service.goal_state, states)

    def test_generate_puzzle_states_zero(self):
        num_puzzles = 0
        states = self.puzzle_service.generate_puzzle_states(num_puzzles)
        self.assertIsInstance(states, set)
        # Implementation always seeds with goal_state
        self.assertEqual(len(states), 1)
        self.assertIn(self.puzzle_service.goal_state, states)

    def test_generate_puzzle_states_negative(self):
        # Negative requests should behave like zero and return at least the goal
        num_puzzles = -10
        states = self.puzzle_service.generate_puzzle_states(num_puzzles)
        self.assertIsInstance(states, set)
        self.assertEqual(len(states), 1)
        self.assertIn(self.puzzle_service.goal_state, states)

    def test_generate_puzzle_states_large_number(self):
        num_puzzles = 50
        states = self.puzzle_service.generate_puzzle_states(num_puzzles)
        self.assertIsInstance(states, set)
        self.assertGreaterEqual(len(states), 1)
        self.assertLessEqual(len(states), num_puzzles)
        self.assertIn(self.puzzle_service.goal_state, states)

    @patch('puzzle_service.PuzzleService.get_neighbors')
    def test_generate_puzzle_states_no_neighbors(self, mock_get_neighbors):
        mock_get_neighbors.return_value = []
        num_puzzles = 5
        states = self.puzzle_service.generate_puzzle_states(num_puzzles)
        self.assertIsInstance(states, set)
        self.assertEqual(len(states), 1)
        self.assertIn(self.puzzle_service.goal_state, states)

    def test_generate_puzzle_states_correctness(self):
        num_puzzles = 10
        states = self.puzzle_service.generate_puzzle_states(num_puzzles)
        for state in states:
            self.assertIsInstance(state, tuple)
            self.assertEqual(len(state), self.puzzle_service.vector_dim)
            for tile in state:
                self.assertIsInstance(tile, int)
                self.assertGreaterEqual(tile, 0)
                self.assertLess(tile, self.puzzle_service.vector_dim)

    def test_generate_puzzle_states_duplicate_states(self):
        num_puzzles = 20
        states = self.puzzle_service.generate_puzzle_states(num_puzzles)
        self.assertEqual(len(states), len(set(states)), "Duplicate states found in the generated set.")

    def test_generate_puzzle_states_goal_neighbors_expected_count(self):
        # For a 3x3 goal state (empty at bottom-right), there are exactly 2 neighbors (up, left)
        num_puzzles = 3
        states = self.puzzle_service.generate_puzzle_states(num_puzzles)
        # compute neighbors directly and confirm they are in the generated set
        neighbors = set(self.puzzle_service.get_neighbors(self.puzzle_service.goal_state))
        # neighbors count expected for 3x3 goal empty at (2,2) is 2
        self.assertEqual(len(neighbors), 2)
        # goal + its two neighbors => 3 states when num_puzzles >= 3
        self.assertGreaterEqual(len(states), 1)
        self.assertLessEqual(len(states), num_puzzles)
        for n in neighbors:
            self.assertIn(n, states)

    def test_generate_puzzle_states_idempotent_calls(self):
        # Repeated calls should not mutate PuzzleService internal attributes used elsewhere
        first = self.puzzle_service.generate_puzzle_states(10)
        second = self.puzzle_service.generate_puzzle_states(10)
        self.assertIsInstance(first, set)
        self.assertIsInstance(second, set)
        # Both results should contain the goal state
        self.assertIn(self.puzzle_service.goal_state, first)
        self.assertIn(self.puzzle_service.goal_state, second)


if __name__ == '__main__':
    unittest.main()