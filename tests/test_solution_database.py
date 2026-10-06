"""Security, format, and immutability tests for the compact solution table."""
from dataclasses import FrozenInstanceError
import hashlib
import itertools
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solution_database import (
    FILE_SIZE, GOAL_STATE, HEADER, PERMUTATION_COUNT, SolutionDatabase,
    rank_state, unrank_state,
)

START = (1, 2, 3, 4, 5, 6, 7, 0, 8)


class TestPermutationRanking(unittest.TestCase):
    def test_ranks_match_lexicographic_order(self):
        for expected, state in enumerate(itertools.islice(itertools.permutations(range(9)), 1000)):
            self.assertEqual(rank_state(state), expected)
            self.assertEqual(unrank_state(expected), state)
        self.assertEqual(unrank_state(PERMUTATION_COUNT - 1), tuple(range(8, -1, -1)))
        self.assertEqual(unrank_state(rank_state(GOAL_STATE)), GOAL_STATE)

    def test_invalid_states_are_rejected(self):
        for state in ((), (1,) * 9, (-1, 1, 2, 3, 4, 5, 6, 7, 8),
                      (9, 1, 2, 3, 4, 5, 6, 7, 8),
                      (False, 1, 2, 3, 4, 5, 6, 7, 8),
                      (0.0, 1, 2, 3, 4, 5, 6, 7, 8),
                      ("0", 1, 2, 3, 4, 5, 6, 7, 8)):
            with self.subTest(state=state), self.assertRaises(ValueError):
                rank_state(state)

    def test_invalid_ranks_are_rejected(self):
        for rank in (-1, PERMUTATION_COUNT, True, 1.0):
            with self.subTest(rank=rank), self.assertRaises(ValueError):
                unrank_state(rank)


class TestSolutionDatabase(unittest.TestCase):
    def setUp(self):
        self.database = SolutionDatabase.from_parents({GOAL_STATE: None, START: GOAL_STATE})
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.directory) / "solutions.bin"

    def test_lookup_reconstructs_paths_without_storing_full_paths(self):
        self.assertEqual(self.database.lookup(START), [START, GOAL_STATE])
        self.assertEqual(self.database.lookup(GOAL_STATE), [GOAL_STATE])
        self.assertIsNone(self.database.lookup((1, 2, 3, 4, 5, 6, 0, 7, 8)))
        self.assertEqual(self.database.entry_count, 2)
        self.assertEqual(self.database.maximum_distance, 1)
        self.assertFalse(self.database.is_complete)

    def test_data_is_immutable_and_paths_are_independent(self):
        with self.assertRaises(FrozenInstanceError):
            self.database.entry_count = 3
        with self.assertRaises(TypeError):
            self.database.distances[0] = 0
        with self.assertRaises(TypeError):
            self.database.next_tiles[0] = 0
        path = self.database.lookup(START)
        path.clear()
        self.assertEqual(self.database.lookup(START), [START, GOAL_STATE])

    def test_binary_round_trip_and_fixed_size(self):
        self.database.save(self.path)
        self.assertEqual(self.path.stat().st_size, FILE_SIZE)
        loaded = SolutionDatabase.load(self.path)
        self.assertEqual(loaded, self.database)
        self.assertEqual(loaded.lookup(START), [START, GOAL_STATE])

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            SolutionDatabase.load(self.path)

    def test_truncated_oversized_and_foreign_files_are_rejected(self):
        self.database.save(self.path)
        original = self.path.read_bytes()
        for data in (original[:-1], original + b"x", b"not a solution table"):
            with self.subTest(length=len(data)):
                self.path.write_bytes(data)
                with self.assertRaises(ValueError):
                    SolutionDatabase.load(self.path)

    def test_header_fields_are_validated(self):
        self.database.save(self.path)
        original = self.path.read_bytes()
        header = list(HEADER.unpack(original[:HEADER.size]))
        for field, value in ((0, b"BADMAGIC"), (1, 99), (2, 4), (3, 0), (3, 3),
                             (4, PERMUTATION_COUNT + 1)):
            with self.subTest(field=field, value=value):
                changed = list(header)
                changed[field] = value
                self.path.write_bytes(HEADER.pack(*changed) + original[HEADER.size:])
                with self.assertRaises(ValueError):
                    SolutionDatabase.load(self.path)

    def test_checksum_mismatch_is_rejected(self):
        self.database.save(self.path)
        data = bytearray(self.path.read_bytes())
        data[-1] ^= 1
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "checksum"):
            SolutionDatabase.load(self.path)

    def test_invalid_moves_are_rejected_even_with_recomputed_checksum(self):
        self.database.save(self.path)
        original = self.path.read_bytes()
        payload = bytearray(original[HEADER.size:])
        # Tile 0 is not adjacent to START's blank at index 7.
        payload[PERMUTATION_COUNT + rank_state(START)] = 0
        header = list(HEADER.unpack(original[:HEADER.size]))
        header[-1] = hashlib.sha256(payload).digest()
        self.path.write_bytes(HEADER.pack(*header) + payload)
        with self.assertRaises(ValueError):
            SolutionDatabase.load(self.path)

    def test_invalid_distances_are_rejected_even_with_recomputed_checksum(self):
        self.database.save(self.path)
        original = self.path.read_bytes()
        payload = bytearray(original[HEADER.size:])
        payload[rank_state(START)] = 32
        header = list(HEADER.unpack(original[:HEADER.size]))
        header[-1] = hashlib.sha256(payload).digest()
        self.path.write_bytes(HEADER.pack(*header) + payload)
        with self.assertRaises(ValueError):
            SolutionDatabase.load(self.path)

    def test_non_decreasing_routes_are_rejected(self):
        self.database.save(self.path)
        original = self.path.read_bytes()
        payload = bytearray(original[HEADER.size:])
        payload[rank_state(START)] = 2  # Its successor is still the distance-zero goal.
        header = list(HEADER.unpack(original[:HEADER.size]))
        header[-1] = hashlib.sha256(payload).digest()
        self.path.write_bytes(HEADER.pack(*header) + payload)
        with self.assertRaises(ValueError):
            SolutionDatabase.load(self.path)

    def test_atomic_save_failure_preserves_existing_file(self):
        self.database.save(self.path)
        original = self.path.read_bytes()
        with patch("solution_database.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                self.database.save(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(Path(self.directory).iterdir()), [self.path])

    def test_invalid_parent_trees_are_rejected(self):
        for parents in ({}, {GOAL_STATE: START}, {GOAL_STATE: None, START: START},
                        {GOAL_STATE: None, tuple(range(9)): GOAL_STATE}):
            with self.subTest(parents=parents), self.assertRaises(ValueError):
                SolutionDatabase.from_parents(parents)


if __name__ == "__main__":
    unittest.main()
