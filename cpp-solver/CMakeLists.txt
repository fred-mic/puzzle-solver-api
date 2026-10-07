cmake_minimum_required(VERSION 3.18)

# One module version shared with setuptools; unrelated to the Python version.
file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/../VERSION" MODULE_VERSION LIMIT_COUNT 1)
project(AStarSolverCpp VERSION ${MODULE_VERSION} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Use the pinned pybind11 installed from requirements-build.txt.
find_package(Python 3.13 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

add_executable(puzzle_solver src/main.cpp)
pybind11_add_module(cpp_solver src/bindings.cpp)
target_compile_definitions(cpp_solver PRIVATE VERSION_INFO="${PROJECT_VERSION}")

foreach(target IN ITEMS puzzle_solver cpp_solver)
    if(MSVC)
        target_compile_options(${target} PRIVATE /O2 /W4)
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "^(GNU|Clang|AppleClang)$")
        target_compile_options(${target} PRIVATE -O3 -Wall)
    endif()
endforeach()
