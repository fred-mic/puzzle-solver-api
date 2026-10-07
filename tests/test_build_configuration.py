"""Public native build contract, exercised for both setuptools and CMake in CI."""
from pathlib import Path
import re
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestBuildConfiguration(unittest.TestCase):
    def test_native_version_and_solver(self):
        import cpp_solver

        self.assertEqual(cpp_solver.__version__, (ROOT / "VERSION").read_text().strip())
        self.assertEqual(cpp_solver.solve([1, 2, 3, 4, 5, 6, 7, 0, 8]), [(2, 2)])

    def test_isolated_build_dependencies_match_lock(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        locked = {
            line.strip() for line in (ROOT / "requirements-build.txt").read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertEqual(set(project["build-system"]["requires"]), locked)

    def test_all_dependency_locks_are_exact(self):
        for filename in ("requirements.txt", "requirements-build.txt", "requirements-dev.txt"):
            for line in (ROOT / filename).read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    with self.subTest(filename=filename, requirement=line):
                        self.assertRegex(line, r"^[A-Za-z0-9_.-]+==[^\s;]+(?:\s*;.*)?$")

    def test_runtime_excludes_native_build_tools(self):
        runtime = (ROOT / "requirements.txt").read_text()
        for name in ("pybind11", "setuptools", "wheel", "packaging"):
            self.assertIsNone(re.search(rf"^{name}==", runtime, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
