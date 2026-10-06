"""Compile native solver regressions, including deterministic rehash checks."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "cpp-solver" / "src"
TEST_SOURCE = ROOT / "cpp-solver" / "tests" / "test_solver.cpp"


class TestCppSolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++") or shutil.which("clang++")
        if compiler is None:
            raise unittest.SkipTest("Native regression tests require g++ or clang++")
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        directory = Path(cls.directory.name)
        cls.environment = dict(os.environ)
        cls.environment["PATH"] = str(Path(compiler).parent) + os.pathsep + cls.environment.get("PATH", "")
        suffix = ".exe" if os.name == "nt" else ""
        cls.standard_executable = directory / ("solver-standard" + suffix)
        cls.checked_executable = directory / ("solver-checked" + suffix)

        # Change only the map type in a temporary copy, not production source.
        header = (SOURCE_DIR / "PuzzleSolver.hpp").read_text(encoding="utf-8")
        declaration = "std::unordered_map<State, int, ArrayHasher> g_score;"
        if header.count(declaration) != 1:
            raise AssertionError("Update the checked-map test hook for the score-map declaration")
        header = header.replace(declaration, "test_support::CheckedScoreMap<State, int, ArrayHasher> g_score;")
        (directory / "PuzzleSolver.hpp").write_text(header, encoding="utf-8")

        common = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wpedantic"]
        builds = (
            (cls.standard_executable, ["-I", str(SOURCE_DIR)]),
            (cls.checked_executable, ["-I", str(directory), "-I", str(SOURCE_DIR),
                                      "-DREHASH_CHECKED_SCORE_MAP"]),
        )
        for executable, includes in builds:
            result = subprocess.run(
                common + includes + [str(TEST_SOURCE), "-o", str(executable)],
                env=cls.environment, capture_output=True, text=True, timeout=120,
            )
            if result.returncode:
                raise AssertionError("Native regression build failed:\n" + result.stdout + result.stderr)

    def run_solver(self, executable):
        result = subprocess.run(
            [str(executable)], env=self.environment, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("solvable_cases=7 invalid_checks=6", result.stdout)
        return result.stdout

    def test_native_solver_paths(self):
        self.run_solver(self.standard_executable)

    def test_rehash_checked_score_map(self):
        output = self.run_solver(self.checked_executable)
        rehashes = int(output.split("rehashes=")[1])
        self.assertGreater(rehashes, 1)


if __name__ == "__main__":
    unittest.main()
