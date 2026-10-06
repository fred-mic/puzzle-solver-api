"""Tests for the required native solver and Python/native result conversion."""
import builtins
import importlib.util
import os
from pathlib import Path
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

SERVICE_PATH = Path(__file__).resolve().parents[1] / "puzzle_service.py"


def load_service(backend=None, import_error=None):
    """Load an isolated service module with a controlled native import."""
    spec = importlib.util.spec_from_file_location("native_backend_test_service", SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    real_import = builtins.__import__

    def controlled_import(name, *args, **kwargs):
        if name == "cpp_solver":
            if import_error is not None:
                raise import_error
            if backend is None:
                raise ModuleNotFoundError("No module named 'cpp_solver'", name="cpp_solver")
            return backend
        return real_import(name, *args, **kwargs)

    with patch.dict(os.environ, {"API_SECRET_TOKEN": "native-backend-test-token"}):
        with patch("builtins.__import__", side_effect=controlled_import):
            spec.loader.exec_module(module)
    return module


class TestNativeBackend(unittest.TestCase):
    def make_service(self, result):
        backend = ModuleType("cpp_solver")
        backend.solve = Mock(return_value=result)
        return load_service(backend).PuzzleService(), backend.solve

    def test_missing_module_fails_during_import_with_build_instructions(self):
        with self.assertRaisesRegex(ImportError, "python setup.py build_ext --inplace") as error:
            load_service()
        self.assertIn("cpp_solver", str(error.exception))
        self.assertIsInstance(error.exception.__cause__, ModuleNotFoundError)

    def test_broken_extension_preserves_original_import_error(self):
        cause = ImportError("DLL load failed: incompatible native library")
        with self.assertRaisesRegex(ImportError, "cpp_solver") as error:
            load_service(import_error=cause)
        self.assertIs(error.exception.__cause__, cause)

    def test_solver_delegates_to_native_module(self):
        moves = [(2, 2)]
        service, solve = self.make_service(moves)
        state = (1, 2, 3, 4, 5, 6, 7, 0, 8)
        self.assertIs(service.solve_with_a_star(state), moves)
        solve.assert_called_once_with(list(state))

    def test_empty_and_missing_native_paths_are_preserved(self):
        state = (1, 2, 3, 4, 5, 6, 7, 8, 0)
        for result in ([], None):
            with self.subTest(result=result):
                service, solve = self.make_service(result)
                self.assertIs(service.solve_with_a_star(state), result)
                solve.assert_called_once_with(list(state))

    def test_native_errors_propagate_without_python_fallback(self):
        service, solve = self.make_service(None)
        solve.side_effect = RuntimeError("native solve failed")
        with self.assertRaisesRegex(RuntimeError, "native solve failed"):
            service.solve_with_a_star((1, 2, 3, 4, 5, 6, 7, 0, 8))

    def test_native_moves_are_converted_to_solution_states(self):
        service, solve = self.make_service([(2, 2)])
        state = (1, 2, 3, 4, 5, 6, 7, 0, 8)
        goal = (1, 2, 3, 4, 5, 6, 7, 8, 0)
        self.assertEqual(service.solve_single_puzzle(state), [state, goal])
        solve.assert_called_once_with(list(state))

    def test_uncached_solution_uses_native_solver_without_mutating_service(self):
        service, solve = self.make_service([(2, 2)])
        state = (1, 2, 3, 4, 5, 6, 7, 0, 8)
        expected = [state, (1, 2, 3, 4, 5, 6, 7, 8, 0)]
        self.assertEqual(service.solve_using_database(state), expected)
        self.assertEqual(service.solve_using_database(state), expected)
        self.assertEqual(solve.call_count, 2)
        self.assertIsNone(service.database)
        self.assertEqual(service.database_entries, 0)


if __name__ == "__main__":
    unittest.main()
