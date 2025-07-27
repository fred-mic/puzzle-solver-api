# CMakeLists.txt

cmake_minimum_required(VERSION 3.14)
project(AStarSolverCpp)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- Target 1: The Standalone C++ Executable ---
add_executable(puzzle_solver src/main.cpp)
target_compile_options(puzzle_solver PRIVATE -O3 -Wall)
# --- End of Target 1 ---


# --- Target 2: The Python Module using pybind11 ---
# Fetch pybind11 from GitHub automatically. This avoids needing to install it manually.
include(FetchContent)
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG        v2.12.0 # Use a specific, stable version
)
FetchContent_MakeAvailable(pybind11)

# Find the Python development libraries
find_package(Python REQUIRED COMPONENTS Interpreter Development)

# This special pybind11 function creates a Python module (.so file).
# It handles all the complex linking and compiler flags for you.
# The first argument is the name of the module.
pybind11_add_module(cpp_solver src/bindings.cpp)

target_compile_definitions(cpp_solver PRIVATE VERSION_INFO=3.12.3) # Use other version if 3.12.3 is not available
# --- End of Target 2 ---