from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup
import glob

cpp_files = glob.glob("cpp-solver/src/bindings.cpp")

ext_modules = [
    Pybind11Extension(
        "cpp_solver",  # Name of your Python module
        cpp_files
    ),
]

setup(
    name="cpp_solver",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=True
)