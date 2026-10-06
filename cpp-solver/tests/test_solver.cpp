#include "CheckedScoreMap.hpp"
#include "PuzzleSolver.hpp"

#include <array>
#include <iostream>
#include <stdexcept>

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        struct Case { State state; std::size_t distance; };
        const std::array<Case, 7> cases{{
            {{1, 2, 3, 4, 5, 6, 7, 8, 0}, 0},
            {{1, 2, 3, 4, 5, 6, 7, 0, 8}, 1},
            {{1, 2, 3, 4, 5, 6, 0, 7, 8}, 2},
            {{0, 1, 3, 4, 2, 5, 7, 8, 6}, 4},
            {{1, 0, 3, 4, 8, 2, 6, 7, 5}, 17},
            {{3, 8, 5, 6, 4, 7, 0, 1, 2}, 22},
            {{8, 6, 7, 2, 5, 4, 3, 0, 1}, 31},
        }};
        const State goal{1, 2, 3, 4, 5, 6, 7, 8, 0};
        PuzzleSolver solver;
        for (const auto& test : cases) {
            const auto path = solver.solve_with_a_star(test.state);
            require(path.has_value(), "missing solution");
            require(path->size() == test.distance, "non-optimal solution length");
            State state = test.state;
            for (const auto& move : *path) {
                const auto empty = std::find(state.begin(), state.end(), 0);
                const int blank = static_cast<int>(empty - state.begin());
                require(move.first >= 0 && move.first < 3 && move.second >= 0 && move.second < 3,
                        "move coordinates out of bounds");
                require(std::abs(blank / 3 - move.first) + std::abs(blank % 3 - move.second) == 1,
                        "illegal move");
                const auto target = static_cast<std::size_t>(move.first * 3 + move.second);
                std::swap(state[static_cast<std::size_t>(blank)], state[target]);
            }
            require(state == goal, "path does not end at goal");
        }
        const std::array<State, 5> invalid{{
            {1, 2, 3, 4, 5, 6, 8, 7, 0},
            {1, 2, 3, 4, 5, 6, 7, 7, 0},
            {-1, 2, 3, 4, 5, 6, 7, 8, 0},
            {9, 2, 3, 4, 5, 6, 7, 8, 0},
            {1, 2, 3, 4, 5, 6, 7, 8, 8},
        }};
        for (const auto& state : invalid) {
            require(!solver.solve_with_a_star(state).has_value(), "invalid state was accepted");
        }
        bool rejected_grid = false;
        try { PuzzleSolver unsupported(4); }
        catch (const std::invalid_argument&) { rejected_grid = true; }
        require(rejected_grid, "unsupported grid was accepted");
#ifdef REHASH_CHECKED_SCORE_MAP
        require(test_support::score_map_rehashes > 1, "test did not exercise map growth");
#endif
        std::cout << "solvable_cases=7 invalid_checks=6 rehashes="
                  << test_support::score_map_rehashes << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
