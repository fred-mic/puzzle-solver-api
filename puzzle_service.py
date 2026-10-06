"""Puzzle solving with an immutable, data-only precomputed solution table."""
from collections import deque
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm

try:
    import cpp_solver
except ImportError as exc:
    raise ImportError(
        "The required 'cpp_solver' native extension could not be imported. "
        "Build or reinstall it with 'python setup.py build_ext --inplace' "
        "using the same Python environment as the application."
    ) from exc

from solution_database import GOAL_STATE, REACHABLE_COUNT, SolutionDatabase, rank_state

DATABASE_PATH = Path(__file__).resolve().with_name("puzzle_solutions.bin")
logger = logging.getLogger(__name__)


class PuzzleService:
    def __init__(self, grid_size: int = 3):
        if grid_size != 3:
            raise ValueError("PuzzleService only supports 3x3 puzzles.")
        self.grid_size = grid_size
        self.tile_count = 9
        self.goal_state = GOAL_STATE
        self._database: Optional[SolutionDatabase] = None

    @property
    def database(self) -> Optional[SolutionDatabase]:
        return self._database

    @property
    def database_entries(self) -> int:
        database = self._database
        return database.entry_count if database is not None else 0

    def load_database(self, path: Optional[Path] = None):
        """Validate a snapshot before publishing it; fail fast on errors."""
        filename = Path(path) if path is not None else DATABASE_PATH
        try:
            database = SolutionDatabase.load(filename)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Solution table '{filename}' is missing. Run 'python build_db.py'."
            ) from exc
        self._database = database
        logger.info("Loaded %d solution entries from %s", database.entry_count, filename)

    def save_database(self, path: Optional[Path] = None):
        """Persist the offline-built table, never a request-populated cache."""
        database = self._database
        if database is None:
            raise RuntimeError("No solution table to save; build it first.")
        database.save(Path(path) if path is not None else DATABASE_PATH)

    def solve_with_a_star(self, initial_state: Tuple[int, ...]) -> Optional[List[Tuple[int, int]]]:
        """Solve using the required native backend; native errors propagate."""
        return cpp_solver.solve(list(initial_state))

    def solve_single_puzzle(self, initial_state: Tuple[int, ...]) -> List[Tuple[int, ...]]:
        path_of_moves = self.solve_with_a_star(initial_state)
        if path_of_moves is None:
            return []
        path_of_states = [initial_state]
        current_state = list(initial_state)
        for tile_r, tile_c in path_of_moves:
            blank = current_state.index(0)
            target = tile_r * self.grid_size + tile_c
            current_state[blank], current_state[target] = current_state[target], current_state[blank]
            path_of_states.append(tuple(current_state))
        return path_of_states

    def get_neighbors(self, state: Tuple[int, ...]) -> List[Tuple[int, ...]]:
        neighbors = []
        blank = state.index(0)
        empty_r, empty_c = divmod(blank, self.grid_size)
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            tile_r, tile_c = empty_r + dr, empty_c + dc
            if 0 <= tile_r < self.grid_size and 0 <= tile_c < self.grid_size:
                target = tile_r * self.grid_size + tile_c
                following = list(state)
                following[blank], following[target] = following[target], following[blank]
                neighbors.append(tuple(following))
        return neighbors

    def _reverse_bfs_tree(
        self, num_puzzles: int
    ) -> Dict[Tuple[int, ...], Optional[Tuple[int, ...]]]:
        """Map each discovered state to its next state on a shortest path to goal."""
        limit = min(REACHABLE_COUNT, max(1, num_puzzles))
        parents = {self.goal_state: None}
        queue = deque([self.goal_state])
        with tqdm(total=limit, initial=1, desc="Reverse BFS") as progress:
            while queue and len(parents) < limit:
                current = queue.popleft()
                for neighbor in self.get_neighbors(current):
                    if neighbor in parents:
                        continue
                    parents[neighbor] = current
                    queue.append(neighbor)
                    progress.update(1)
                    if len(parents) == limit:
                        break
        return parents

    def generate_puzzle_states(self, num_puzzles: int) -> set:
        """Return at most the requested positive number of reachable states."""
        return set(self._reverse_bfs_tree(num_puzzles))

    def build_solution_database(self, num_puzzles: int):
        """Build an immutable distance/next-move table offline using reverse BFS."""
        database = SolutionDatabase.from_parents(self._reverse_bfs_tree(num_puzzles))
        self._database = database
        logger.info("Built %d solution entries using reverse BFS", database.entry_count)

    def solve_using_database(self, query_state: Tuple[int, ...]) -> List[Tuple[int, ...]]:
        """Read one immutable snapshot; never cache misses or mutate stored data."""
        state = tuple(query_state)
        rank_state(state)  # Validate before either table indexing or native search.
        database = self._database
        if database is not None:
            path = database.lookup(state)
            if path is not None:
                return path
            if database.is_complete:
                return []  # Every absent valid permutation is unsolvable.
        return self.solve_single_puzzle(state)
