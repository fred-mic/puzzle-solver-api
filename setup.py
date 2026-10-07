from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

MODULE_VERSION = Path(__file__).with_name("VERSION").read_text(encoding="utf-8").strip()

ext_modules = [
    Pybind11Extension(
        "cpp_solver",
        ["cpp-solver/src/bindings.cpp"],
        cxx_std=17,
        define_macros=[("VERSION_INFO", f'"{MODULE_VERSION}"')],
    ),
]

setup(
    name="cpp_solver",
    version=MODULE_VERSION,
    python_requires=">=3.13",
    packages=[],
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
