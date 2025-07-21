// src/main.cpp
#include "PuzzleSolver.hpp"
#include <string> // For std::stoi

// Helper function to print a path (no change)
void print_path(const Path& path) {
    std::cout << "Solution Path (list of moves (row, col)):" << std::endl;
    std::cout << "[";
    for (size_t i = 0; i < path.size(); ++i) {
        std::cout << "(" << path[i].first << ", " << path[i].second << ")";
        if (i < path.size() - 1) {
            std::cout << ", ";
        }
    }
    std::cout << "]" << std::endl;
}

int main(int argc, char* argv[]) {
    // Check if the user provided the correct number of arguments
    if (argc != 10) {
        std::cerr << "Usage: " << argv[0] << " <t1> <t2> ... <t9>" << std::endl;
        std::cerr << "Provide the 9 tile numbers (use 0 for empty space)." << std::endl;
        std::cerr << "Example: " << argv[0] << " 1 2 3 4 5 6 0 7 8" << std::endl;
        return 1; // Return an error code
    }

    State initial_state;
    try {
        for (int i = 0; i < 9; ++i) {
            // argv[0] is the program name, so we start from argv[1]
            initial_state[i] = std::stoi(argv[i + 1]);
        }
    } catch (const std::exception& e) {
        std::cerr << "Error: Invalid number provided. Please provide only integers." << std::endl;
        return 1;
    }
    
    PuzzleSolver solver;
    std::cout << "Solving puzzle..." << std::endl;
    std::optional<Path> solution = solver.solve_with_a_star(initial_state);

    if (solution.has_value()) {
        std::cout << "Solution found in " << solution->size() << " moves." << std::endl;
        print_path(solution.value());
    } else {
        std::cout << "No solution could be found for the given puzzle." << std::endl;
    }

    return 0;
}