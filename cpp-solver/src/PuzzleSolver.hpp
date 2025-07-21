// src/PuzzleSolver.hpp
#pragma once // Prevents the header from being included multiple times

#include <iostream>
#include <vector>
#include <array>
#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <cmath>      // For std::abs
#include <algorithm>  // For std::reverse
#include <optional>   // To handle the "no solution" case

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
    PuzzleSolver(int grid_size = 3) :
        grid_size_(grid_size),
        goal_state_({1, 2, 3, 4, 5, 6, 7, 8, 0}) {}

    /**
     * @brief The main A* solver function.
     * @param initial_state The starting state of the puzzle.
     * @return An std::optional containing the path of moves if a solution is found, otherwise std::nullopt.
     */
    std::optional<Path> solve_with_a_star(const State& initial_state) {
        if (initial_state == goal_state_) {
            return Path{}; // Empty path
        }

        // The priority queue stores pairs of (f_score, state).
        // std::greater makes it a min-heap, so the smallest f_score is always at the top.
        using PQElement = std::pair<int, State>;
        std::priority_queue<PQElement, std::vector<PQElement>, std::greater<PQElement>> open_heap;

        // g_score map
        std::unordered_map<State, int, ArrayHasher> g_score;
        
        // came_from map stores: child_state -> {parent_state, move_to_get_here}
        std::unordered_map<State, std::pair<State, Move>, ArrayHasher> came_from;

        // This set is equivalent to Python's open_set_hash
        std::unordered_set<State, ArrayHasher> open_set_hash;

        // Initialize with the start node
        g_score[initial_state] = 0;
        open_heap.push({heuristic(initial_state), initial_state});
        open_set_hash.insert(initial_state);

        while (!open_heap.empty()) {
            State current_state = open_heap.top().second;
            open_heap.pop();
            open_set_hash.erase(current_state);

            if (current_state == goal_state_) {
                return reconstruct_move_path(came_from, current_state);
            }

            int empty_index = -1;
            for (size_t i = 0; i < current_state.size(); ++i) {
                if (current_state[i] == 0) {
                    empty_index = i;
                    break;
                }
            }

            int empty_r = empty_index / grid_size_;
            int empty_c = empty_index % grid_size_;

            // Explore neighbors
            for (const auto& move : std::vector<Move>{{0, 1}, {0, -1}, {1, 0}, {-1, 0}}) {
                int tile_r = empty_r + move.first;
                int tile_c = empty_c + move.second;

                if (tile_r >= 0 && tile_r < grid_size_ && tile_c >= 0 && tile_c < grid_size_) {
                    int tile_index = tile_r * grid_size_ + tile_c;
                    State neighbor_state = current_state;
                    std::swap(neighbor_state[empty_index], neighbor_state[tile_index]);

                    int tentative_g_score = g_score.at(current_state) + 1;

                    if (!g_score.count(neighbor_state) || tentative_g_score < g_score.at(neighbor_state)) {
                        came_from[neighbor_state] = {current_state, {tile_r, tile_c}};
                        g_score[neighbor_state] = tentative_g_score;
                        int f_score = tentative_g_score + heuristic(neighbor_state);

                        if (open_set_hash.find(neighbor_state) == open_set_hash.end()) {
                            open_heap.push({f_score, neighbor_state});
                            open_set_hash.insert(neighbor_state);
                        }
                    }
                }
            }
        }

        return std::nullopt; // No solution found
    }

private:
    int grid_size_;
    State goal_state_;

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