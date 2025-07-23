// src/bindings.cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>      // Required for automatic type conversion (vector, optional, etc.)
#include <pybind11/operators.h> // For comparing states if needed

#include "PuzzleSolver.hpp"

namespace py = pybind11;

// This macro creates a Python module.
// The first argument is the name of the module as it will appear in Python (e.g., `import cpp-solver`).
// The second argument, 'm', is a variable representing the module object.
PYBIND11_MODULE(cpp_solver, m) {
    m.doc() = "High-performance C++ puzzle solver"; // Optional module docstring

    // Expose the 'solve_with_a_star' function to Python.
    // We name it "solve" in Python for convenience.
    // We use a lambda function to wrap the C++ class instantiation and method call.
    m.def("solve", [](const std::vector<int>& state_list) -> std::optional<Path> {
        if (state_list.size() != 9) {
            throw std::runtime_error("Input state must contain exactly 9 integers.");
        }
        
        // Convert the Python list to our C++ State (std::array)
        State initial_state;
        std::copy_n(state_list.begin(), 9, initial_state.begin());
        
        PuzzleSolver solver;
        return solver.solve_with_a_star(initial_state);

    }, "Solves a 3x3 puzzle using the A* algorithm");
}