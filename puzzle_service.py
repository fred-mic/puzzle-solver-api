# puzzle_service.py
import faiss
import numpy as np
import pickle
import heapq
from collections import deque
from typing import List, Tuple, Dict, Optional
import os
from tqdm import tqdm
import time

try:
    import cpp_solver
    CPP_SOLVER_AVAILABLE = True
    print("Successfully imported C++ solver module.")
except ImportError:
    CPP_SOLVER_AVAILABLE = False
    print("WARNING: C++ solver module not found. Falling back to slower Python implementation.")


class PuzzleService:
    """
    Encapsulates all the core logic for solving puzzles and managing the
    solution database. This class does not handle any web requests.
    """
    def __init__(self, grid_size: int = 3):
        self.grid_size = grid_size
        self.vector_dim = self.grid_size ** 2
        self.goal_state = tuple(range(1, self.vector_dim)) + (0,)
        
        # Initialize database components
        self.index: Optional[faiss.Index] = None
        self.state_to_id: Dict[Tuple[int, ...], int] = {}
        self.id_to_state: Dict[int, Tuple[int, ...]] = {}
        self.solutions: Dict[Tuple[int, ...], List[Tuple[int, ...]]] = {}
        
    def initialize_faiss_index(self):
        """Creates a new, empty FAISS index."""
        self.index = faiss.IndexFlatL2(self.vector_dim)

    def state_to_vector(self, state: Tuple[int, ...]) -> np.ndarray:
        max_val = float(self.vector_dim - 1)
        vector = np.array(state, dtype=np.float32) / max_val
        return vector.reshape(1, -1)

    def heuristic(self, state: Tuple[int, ...]) -> int:
        distance = 0
        for i, num in enumerate(state):
            if num != 0:
                goal_index = num - 1
                current_r, current_c = divmod(i, self.grid_size)
                goal_r, goal_c = divmod(goal_index, self.grid_size)
                distance += abs(current_r - goal_r) + abs(current_c - goal_c)
        return distance

    def reconstruct_move_path(self, came_from: Dict, current_state: Tuple[int, ...]) -> List[Tuple[int, int]]:
        path = []
        while came_from[current_state] is not None:
            parent_state, move_coords = came_from[current_state]
            path.append(move_coords)
            current_state = parent_state
        return path[::-1]

    def solve_with_a_star(self, initial_state: Tuple[int, ...]) -> Optional[List[Tuple[int, int]]]:
        if CPP_SOLVER_AVAILABLE:
            # pybind11 automatically converts the C++ std::optional<Path>
            # to either a Python list of tuples or None. It's seamless.
            return cpp_solver.solve(list(initial_state))
        else:
            if initial_state == self.goal_state: 
                return []
            open_heap = [(self.heuristic(initial_state), initial_state)]
            open_set_hash = {initial_state}
            came_from = {initial_state: None}
            g_score = {initial_state: 0}
            
            while open_heap:
                current_state = heapq.heappop(open_heap)[1]
                open_set_hash.remove(current_state)
                if current_state == self.goal_state: return self.reconstruct_move_path(came_from, current_state)
                empty_index = current_state.index(0)
                empty_r, empty_c = divmod(empty_index, self.grid_size)
                for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    tile_r, tile_c = empty_r + dr, empty_c + dc
                    if not (0 <= tile_r < self.grid_size and 0 <= tile_c < self.grid_size): continue
                    tile_index = tile_r * self.grid_size + tile_c
                    new_state_list = list(current_state)
                    new_state_list[empty_index], new_state_list[tile_index] = new_state_list[tile_index], new_state_list[empty_index]
                    neighbor_state = tuple(new_state_list)
                    tentative_g_score = g_score[current_state] + 1
                    if tentative_g_score < g_score.get(neighbor_state, float('inf')):
                        came_from[neighbor_state] = (current_state, (tile_r, tile_c))
                        g_score[neighbor_state] = tentative_g_score
                        f_score = tentative_g_score + self.heuristic(neighbor_state)
                        if neighbor_state not in open_set_hash:
                            heapq.heappush(open_heap, (f_score, neighbor_state))
                            open_set_hash.add(neighbor_state)
            return None

    def solve_single_puzzle(self, initial_state: Tuple[int, ...]) -> List[Tuple[int, ...]]:
        path_of_moves = self.solve_with_a_star(initial_state)
        if path_of_moves is None: return []
        if not path_of_moves: return [initial_state]
        path_of_states = [initial_state]
        current_state_list = list(initial_state)
        for move in path_of_moves:
            empty_index = current_state_list.index(0)
            tile_r, tile_c = move
            tile_index = tile_r * self.grid_size + tile_c
            current_state_list[empty_index], current_state_list[tile_index] = current_state_list[tile_index], current_state_list[empty_index]
            path_of_states.append(tuple(current_state_list))
        return path_of_states

    def get_neighbors(self, state: Tuple[int, ...]) -> List[Tuple[int, ...]]:
        neighbors = []
        empty_index = state.index(0)
        empty_r, empty_c = divmod(empty_index, self.grid_size)
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            tile_r, tile_c = empty_r + dr, empty_c + dc
            if 0 <= tile_r < self.grid_size and 0 <= tile_c < self.grid_size:
                tile_index = tile_r * self.grid_size + tile_c
                new_state = list(state)
                new_state[empty_index], new_state[tile_index] = new_state[tile_index], new_state[empty_index]
                neighbors.append(tuple(new_state))
        return neighbors

    def generate_puzzle_states(self, num_puzzles: int) -> set:
        print(f"Generating {num_puzzles} puzzle states via breadth-first walk from goal...")
        puzzle_states = {self.goal_state}
        queue = deque([self.goal_state])
        pbar = tqdm(total=num_puzzles, desc="Generating States")
        while len(puzzle_states) < num_puzzles and queue:
            current_state = queue.popleft()
            if len(puzzle_states) >= num_puzzles:
                pbar.update(num_puzzles - pbar.n)
                break
            for neighbor in self.get_neighbors(current_state):
                if neighbor not in puzzle_states:
                    puzzle_states.add(neighbor)
                    pbar.update(1)
                    queue.append(neighbor)
        pbar.close()
        return puzzle_states

    def build_solution_database(self, num_puzzles: int):
        puzzle_states = self.generate_puzzle_states(num_puzzles)
        print("\nSolving puzzles and building database...")
        solutions_found = 0
        for state in tqdm(puzzle_states, desc="Solving and Storing"):
            solution_path = self.solve_single_puzzle(state)
            if solution_path:
                self.add_solution_to_database(state, solution_path)
                solutions_found += 1
        print(f"Successfully solved and stored {solutions_found} puzzles")

    def add_solution_to_database(self, state, solution_path):
        if self.index is None: self.initialize_faiss_index()
        vector = self.state_to_vector(state)
        faiss_id = self.index.ntotal
        self.index.add(vector)
        self.state_to_id[state] = faiss_id
        self.id_to_state[faiss_id] = state
        self.solutions[state] = solution_path

    def solve_using_database(self, query_state: Tuple[int, ...]) -> List[Tuple[int, ...]]:
        if query_state in self.solutions:
            print("Found exact solution in database.")
            return self.solutions[query_state]
        print("No exact match in DB. Solving puzzle directly...")
        solution_path = self.solve_single_puzzle(query_state)
        if solution_path:
            print("New puzzle solved! Adding solution to in-memory database.")
            self.add_solution_to_database(query_state, solution_path)
        else:
            print("Direct A* solver could not find a solution for this state.")
        return solution_path

    def save_database(self, filename: str):
        if self.index is None or self.index.ntotal == 0:
            print("Database is empty. Nothing to save.")
            return
        print(f"Saving database to {filename}...")
        faiss.write_index(self.index, f"{filename}.faiss")
        metadata = {'state_to_id': self.state_to_id, 'id_to_state': self.id_to_state, 'solutions': self.solutions}
        with open(f"{filename}_metadata.pkl", 'wb') as f:
            pickle.dump(metadata, f)
        print("Database saved successfully.")

    def load_database(self, filename: str):
        faiss_file = f"{filename}.faiss"
        meta_file = f"{filename}_metadata.pkl"
        if not os.path.exists(faiss_file) or not os.path.exists(meta_file):
            print("Database files not found. Starting with an empty database.")
            self.initialize_faiss_index()
            return
        print(f"Loading database from {filename}...")
        self.index = faiss.read_index(faiss_file)
        with open(meta_file, 'rb') as f:
            metadata = pickle.load(f)
        self.state_to_id = metadata['state_to_id']
        self.id_to_state = metadata['id_to_state']
        self.solutions = metadata['solutions']
        print(f"Database loaded with {self.index.ntotal} solutions.")