from pybind11.setup_helpers import Pybind11Extension, build_ext
from pybind11 import get_cmake_dir
import pybind11
from setuptools import setup, Extension
import glob

# Get all C++ source files
cpp_files = glob.glob("cpp-solver/src/*.cpp")

ext_modules = [
    Pybind11Extension(
        "cpp-solver",  # Name of your Python module
        cpp_files,
        include_dirs=[
            pybind11.get_include(),
            "cpp-solver/src",  # Add your header directory if needed
        ],
        cxx_std=17,  # C++ standard (11, 14, 17, 20)
        # Add any additional compile flags
        extra_compile_args=["-O3"],
    ),
]

setup(
    name="cpp-solver",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.6",
)