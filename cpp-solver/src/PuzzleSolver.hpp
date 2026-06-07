// src/PuzzleSolver.hpp
#pragma once // Prevents the header from being included multiple times

#include <array>
#include <algorithm>  // For std::reverse
#include <cmath>      // For std::abs
#include <cstddef>
#include <optional>   // To handle the "no solution" case
#include <queue>
#include <stdexcept>
#include <unordered_map>
#include <vector>

// --- Type Aliases for Clarity (similar to Python's 'from typing import ...') ---
using State = std::array<int, 9>;
using Move = std::pair<int, int>;
using Path = std::vector<Move>;

// --- Custom Hasher for std::array ---
// This is required to use std::array as a key in unordered_map/unordered_set.
struct ArrayHasher {
    std::size_t operator()(const State& a) const {
        std::size_t h = 0;
        for (auto e : a) {
            h ^= std::hash<int>{}(e) + 0x9e3779b9 + (h << 6) + (h >> 2);
        }
        return h;
    }
};

class PuzzleSolver {
public:
    explicit PuzzleSolver(int grid_size = 3) :
        grid_size_(grid_size),
        goal_state_({1, 2, 3, 4, 5, 6, 7, 8, 0}) {
        if (grid_size_ != kGridSize) {
            throw std::invalid_argument("PuzzleSolver only supports 3x3 puzzles.");
        }
    }

    /**
     * @brief The main A* solver function.
     * @param initial_state The starting state of the puzzle.
     * @return An std::optional containing the path of moves if a solution is found, otherwise std::nullopt.
     */
    std::optional<Path> solve_with_a_star(const State& initial_state) {
        if (!is_valid_state(initial_state) || !is_solvable(initial_state)) {
            return std::nullopt;
        }

        if (initial_state == goal_state_) {
            return Path{}; // Empty path
        }

        std::priority_queue<QueueNode, std::vector<QueueNode>, QueueNodeComparator> open_heap;

        // g_score map
        std::unordered_map<State, int, ArrayHasher> g_score;
        
        // came_from map stores: child_state -> {parent_state, move_to_get_here}
        std::unordered_map<State, std::pair<State, Move>, ArrayHasher> came_from;

        // Initialize with the start node
        g_score[initial_state] = 0;
        open_heap.push({heuristic(initial_state), 0, initial_state});

        while (!open_heap.empty()) {
            QueueNode current = open_heap.top();
            open_heap.pop();

            const auto current_g_it = g_score.find(current.state);
            if (current_g_it == g_score.end() || current.g_score != current_g_it->second) {
                continue;
            }

            const State& current_state = current.state;

            if (current_state == goal_state_) {
                return reconstruct_move_path(came_from, current_state);
            }

            int empty_index = find_empty_index(current_state);
            int empty_r = empty_index / grid_size_;
            int empty_c = empty_index % grid_size_;

            // Explore neighbors
            for (const auto& move : kDirections) {
                int tile_r = empty_r + move.first;
                int tile_c = empty_c + move.second;

                if (tile_r >= 0 && tile_r < grid_size_ && tile_c >= 0 && tile_c < grid_size_) {
                    int tile_index = tile_r * grid_size_ + tile_c;
                    State neighbor_state = current_state;
                    std::swap(neighbor_state[empty_index], neighbor_state[tile_index]);

                    int tentative_g_score = current_g_it->second + 1;
                    auto neighbor_g_it = g_score.find(neighbor_state);

                    if (neighbor_g_it == g_score.end() || tentative_g_score < neighbor_g_it->second) {
                        came_from[neighbor_state] = {current_state, {tile_r, tile_c}};
                        g_score[neighbor_state] = tentative_g_score;
                        int f_score = tentative_g_score + heuristic(neighbor_state);
                        open_heap.push({f_score, tentative_g_score, neighbor_state});
                    }
                }
            }
        }

        return std::nullopt; // No solution found
    }

private:
    static constexpr int kGridSize = 3;
    static constexpr int kTileCount = kGridSize * kGridSize;
    static constexpr std::array<Move, 4> kDirections{{{0, 1}, {0, -1}, {1, 0}, {-1, 0}}};

    struct QueueNode {
        int f_score;
        int g_score;
        State state;
    };

    struct QueueNodeComparator {
        bool operator()(const QueueNode& lhs, const QueueNode& rhs) const {
            if (lhs.f_score != rhs.f_score) {
                return lhs.f_score > rhs.f_score;
            }
            return lhs.g_score < rhs.g_score;
        }
    };

    int grid_size_;
    State goal_state_;

    bool is_valid_state(const State& state) const {
        std::array<int, kTileCount> counts{};
        for (int tile : state) {
            if (tile < 0 || tile >= kTileCount) {
                return false;
            }
            ++counts[tile];
        }

        return std::all_of(counts.begin(), counts.end(), [](int count) {
            return count == 1;
        });
    }

    bool is_solvable(const State& state) const {
        int inversions = 0;
        for (std::size_t i = 0; i < state.size(); ++i) {
            if (state[i] == 0) {
                continue;
            }
            for (std::size_t j = i + 1; j < state.size(); ++j) {
                if (state[j] != 0 && state[i] > state[j]) {
                    ++inversions;
                }
            }
        }

        return inversions % 2 == 0;
    }

    int find_empty_index(const State& state) const {
        const auto empty_it = std::find(state.begin(), state.end(), 0);
        return static_cast<int>(std::distance(state.begin(), empty_it));
    }

    /**
     * @brief Calculates the Manhattan distance heuristic.
     */
    int heuristic(const State& state) const {
        int distance = 0;
        for (size_t i = 0; i < state.size(); ++i) {
            int num = state[i];
            if (num != 0) {
                int goal_index = num - 1;
                int current_r = i / grid_size_;
                int current_c = i % grid_size_;
                int goal_r = goal_index / grid_size_;
                int goal_c = goal_index % grid_size_;
                distance += std::abs(current_r - goal_r) + std::abs(current_c - goal_c);
            }
        }
        return distance;
    }

    /**
     * @brief Reconstructs the path of moves from the came_from map.
     */
    Path reconstruct_move_path(
        const std::unordered_map<State, std::pair<State, Move>, ArrayHasher>& came_from,
        State current_state
    ) const {
        Path total_path;
        while (came_from.count(current_state)) {
            const auto& record = came_from.at(current_state);
            total_path.push_back(record.second);
            current_state = record.first;
        }
        std::reverse(total_path.begin(), total_path.end());
        return total_path;
    }
};