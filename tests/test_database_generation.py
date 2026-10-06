"""Regression tests for reverse-BFS generation and non-mutating table reads."""
from collections import deque
from pathlib import Path
import tempfile
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from test_native_backend import load_service


def independent_neighbors(state):
    blank = state.index(0)
    adjacency = ((1, 3), (0, 2, 4), (1, 5), (0, 4, 6), (1, 3, 5, 7),
                 (2, 4, 8), (3, 7), (4, 6, 8), (5, 7))
    for target in adjacency[blank]:
        neighbor = list(state)
        neighbor[blank], neighbor[target] = neighbor[target], neighbor[blank]
        yield tuple(neighbor)


def independent_distances(goal, max_depth):
    distances = {goal: 0}
    queue = deque([goal])
    while queue:
        state = queue.popleft()
        if distances[state] == max_depth:
            continue
        for neighbor in independent_neighbors(state):
            if neighbor not in distances:
                distances[neighbor] = distances[state] + 1
                queue.append(neighbor)
    return distances


class TestDatabaseGeneration(unittest.TestCase):
    def setUp(self):
        self.backend = ModuleType("cpp_solver")
        self.backend.solve = Mock(side_effect=AssertionError("BFS must not invoke A*"))
        self.module = load_service(self.backend)
        self.service = self.module.PuzzleService()

    def test_reverse_bfs_paths_are_legal_and_optimal_without_a_star(self):
        with patch.object(
            self.service, "solve_with_a_star", side_effect=AssertionError("A* called")
        ) as a_star:
            self.service.build_solution_database(128)
        a_star.assert_not_called()
        self.backend.solve.assert_not_called()
        distances = independent_distances(self.service.goal_state, 8)
        self.assertEqual(self.service.database_entries, 128)
        for state in self.service.database.iter_states():
            with self.subTest(state=state):
                path = self.service.solve_using_database(state)
                self.assertEqual(path[0], state)
                self.assertEqual(path[-1], self.service.goal_state)
                self.assertEqual(len(path) - 1, distances[state])
                for current, following in zip(path, path[1:]):
                    self.assertIn(following, independent_neighbors(current))

    def test_generation_respects_exact_positive_limits(self):
        for count in (2, 5, 10, 50, 128):
            with self.subTest(count=count):
                states = self.service.generate_puzzle_states(count)
                self.assertEqual(len(states), count)
                self.assertIn(self.service.goal_state, states)

    def test_rebuild_replaces_old_entries(self):
        self.service.build_solution_database(20)
        self.service.build_solution_database(1)
        goal = self.service.goal_state
        self.assertEqual(list(self.service.database.iter_states()), [goal])
        self.assertEqual(self.service.solve_using_database(goal), [goal])
        self.assertEqual(self.service.database_entries, 1)

    def test_table_encoding_is_deterministic(self):
        self.service.build_solution_database(20)
        original = self.service.database
        self.service.build_solution_database(20)
        self.assertEqual(self.service.database, original)
        self.assertEqual(self.service.database_entries, 20)

    def test_artifact_round_trip(self):
        self.service.build_solution_database(20)
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "solutions.bin"
            self.service.save_database(filename)
            loaded = self.module.PuzzleService()
            loaded.load_database(filename)
            self.assertEqual(loaded.database, self.service.database)
            self.assertEqual(loaded.database_entries, 20)
            for state in self.service.database.iter_states():
                self.assertEqual(loaded.solve_using_database(state), self.service.solve_using_database(state))

    def test_exhausted_search_terminates(self):
        with patch.object(self.service, "get_neighbors", return_value=[]):
            self.service.build_solution_database(20)
        self.assertEqual(self.service.database_entries, 1)
        self.backend.solve.assert_not_called()

    def test_hit_does_not_mutate_snapshot_and_returns_fresh_paths(self):
        self.service.build_solution_database(20)
        snapshot = self.service.database
        states = list(snapshot.iter_states())
        path = self.service.solve_using_database(states[0])
        expected = list(path)
        path.clear()
        self.assertEqual(self.service.solve_using_database(states[0]), expected)
        self.assertIs(self.service.database, snapshot)
        self.backend.solve.assert_not_called()

    def test_partial_table_misses_do_not_mutate_or_cache(self):
        self.service.build_solution_database(1)
        snapshot = self.service.database
        state = (1, 2, 3, 4, 5, 6, 7, 0, 8)
        self.backend.solve.side_effect = None
        self.backend.solve.return_value = [(2, 2)]
        for _ in range(2):
            self.assertEqual(self.service.solve_using_database(state), [state, self.service.goal_state])
        self.assertEqual(self.backend.solve.call_count, 2)
        self.assertIs(self.service.database, snapshot)
        self.assertEqual(self.service.database_entries, 1)

    def test_failed_load_preserves_existing_snapshot(self):
        self.service.build_solution_database(1)
        snapshot = self.service.database
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "bad.bin"
            filename.write_bytes(b"invalid")
            with self.assertRaises(ValueError):
                self.service.load_database(filename)
            self.assertIs(self.service.database, snapshot)
            with self.assertRaisesRegex(FileNotFoundError, "python build_db.py"):
                self.service.load_database(Path(directory) / "missing.bin")
            self.assertIs(self.service.database, snapshot)

    def test_save_without_a_built_table_fails(self):
        with self.assertRaises(RuntimeError):
            self.service.save_database()

    def test_invalid_query_does_not_reach_native_search(self):
        with self.assertRaises(ValueError):
            self.service.solve_using_database((1,) * 9)
        self.backend.solve.assert_not_called()
        self.assertIsNone(self.service.database)

    def test_unsupported_grid_is_rejected(self):
        with self.assertRaises(ValueError):
            self.module.PuzzleService(grid_size=4)


if __name__ == "__main__":
    unittest.main()
