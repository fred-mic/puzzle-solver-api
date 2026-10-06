"""Versioned, non-executable, immutable solution tables for the 3x3 puzzle."""
from dataclasses import dataclass, field
import hashlib
import math
import os
from pathlib import Path
import struct
import tempfile
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

State = Tuple[int, ...]
GRID_SIZE = 3
TILE_COUNT = 9
PERMUTATION_COUNT = math.factorial(TILE_COUNT)
REACHABLE_COUNT = PERMUTATION_COUNT // 2
MAX_MOVES = 31
UNKNOWN = 255
GOAL_STATE = (1, 2, 3, 4, 5, 6, 7, 8, 0)
ADJACENCY = ((1, 3), (0, 2, 4), (1, 5), (0, 4, 6), (1, 3, 5, 7),
             (2, 4, 8), (3, 7), (4, 6, 8), (5, 7))
FACTORIALS = tuple(math.factorial(i) for i in range(TILE_COUNT))
MAGIC = b"8PUZDB\x00\x00"
VERSION = 1
# magic, version, grid size, reachable entries, permutation slots, payload SHA-256
HEADER = struct.Struct("<8sBBII32s")
FILE_SIZE = HEADER.size + 2 * PERMUTATION_COUNT


def rank_state(state: Sequence[int]) -> int:
    """Return the Lehmer rank of a strict permutation of integers 0..8."""
    if len(state) != TILE_COUNT:
        raise ValueError("Invalid puzzle state. Must be a permutation of integers 0..8.")
    rank = seen = 0
    for position, tile in enumerate(state):
        if type(tile) is not int or not 0 <= tile < TILE_COUNT or seen & (1 << tile):
            raise ValueError("Invalid puzzle state. Must be a permutation of integers 0..8.")
        lower_unused = tile - (seen & ((1 << tile) - 1)).bit_count()
        rank += lower_unused * FACTORIALS[TILE_COUNT - 1 - position]
        seen |= 1 << tile
    return rank


def unrank_state(rank: int) -> State:
    if type(rank) is not int or not 0 <= rank < PERMUTATION_COUNT:
        raise ValueError("Permutation rank is outside the 3x3 state space.")
    remaining = list(range(TILE_COUNT))
    state = []
    for factor in reversed(FACTORIALS):
        index, rank = divmod(rank, factor)
        state.append(remaining.pop(index))
    return tuple(state)


def _move(state: State, target: int) -> State:
    blank = state.index(0)
    if target not in ADJACENCY[blank]:
        raise ValueError("Solution table contains an illegal move.")
    following = list(state)
    following[blank], following[target] = following[target], following[blank]
    return tuple(following)


@dataclass(frozen=True)
class SolutionDatabase:
    distances: bytes = field(repr=False)
    next_tiles: bytes = field(repr=False)
    entry_count: int

    def __post_init__(self):
        if (type(self.distances) is not bytes or type(self.next_tiles) is not bytes
                or len(self.distances) != PERMUTATION_COUNT
                or len(self.next_tiles) != PERMUTATION_COUNT):
            raise ValueError("Solution table arrays must be fixed-size immutable bytes.")
        if type(self.entry_count) is not int or not 1 <= self.entry_count <= REACHABLE_COUNT:
            raise ValueError("Invalid solution table entry count.")
        if PERMUTATION_COUNT - self.distances.count(b"\xff") != self.entry_count:
            raise ValueError("Solution table entry count does not match its payload.")
        goal_rank = rank_state(GOAL_STATE)
        if self.distances[goal_rank] != 0 or self.distances.count(b"\x00") != 1:
            raise ValueError("Only the canonical goal may have distance zero.")
        for distance, target in zip(self.distances, self.next_tiles):
            if distance == UNKNOWN:
                if target != UNKNOWN:
                    raise ValueError("Unknown states must not contain moves.")
            elif distance > MAX_MOVES:
                raise ValueError("Solution distance exceeds the 8-puzzle maximum.")
            elif distance == 0:
                if target != UNKNOWN:
                    raise ValueError("The goal must not contain a next move.")
            elif target >= TILE_COUNT:
                raise ValueError("Invalid next tile index in solution table.")

    @property
    def is_complete(self) -> bool:
        return self.entry_count == REACHABLE_COUNT

    @property
    def maximum_distance(self) -> int:
        return max(self.distances.replace(b"\xff", b""))

    def iter_states(self) -> Iterator[State]:
        for rank, distance in enumerate(self.distances):
            if distance != UNKNOWN:
                yield unrank_state(rank)

    def lookup(self, state: Sequence[int]) -> Optional[List[State]]:
        """Return a fresh path, or None for a state absent from this table."""
        current = tuple(state)
        rank = rank_state(current)
        distance = self.distances[rank]
        if distance == UNKNOWN:
            return None
        path = [current]
        # Each step must decrease distance, bounding reconstruction to 31 moves.
        while distance:
            current = _move(current, self.next_tiles[rank])
            rank = rank_state(current)
            if self.distances[rank] != distance - 1:
                raise ValueError("Solution table route does not decrease distance.")
            distance -= 1
            path.append(current)
        return path

    @classmethod
    def from_parents(cls, parents: Dict[State, Optional[State]]) -> "SolutionDatabase":
        """Encode a reverse-BFS tree in discovery order without storing full paths."""
        if GOAL_STATE not in parents or parents[GOAL_STATE] is not None:
            raise ValueError("Reverse-BFS tree must be rooted at the canonical goal.")
        distances = bytearray([UNKNOWN]) * PERMUTATION_COUNT
        next_tiles = bytearray([UNKNOWN]) * PERMUTATION_COUNT
        for state, parent in parents.items():
            rank = rank_state(state)
            if state == GOAL_STATE:
                distances[rank] = 0
                continue
            if parent is None:
                raise ValueError("Only the goal may have no parent.")
            parent_rank = rank_state(parent)
            if distances[parent_rank] == UNKNOWN:
                raise ValueError("BFS parents must precede their children.")
            target = parent.index(0)
            if _move(state, target) != parent:
                raise ValueError("BFS parent is not a legal neighbor.")
            distance = distances[parent_rank] + 1
            if distance > MAX_MOVES:
                raise ValueError("BFS distance exceeds the 8-puzzle maximum.")
            distances[rank] = distance
            next_tiles[rank] = target
        return cls(bytes(distances), bytes(next_tiles), len(parents))

    def _validate_routes(self):
        """Check legal descending routes and consistent neighboring distances."""
        for rank, distance in enumerate(self.distances):
            if distance == UNKNOWN:
                continue
            state = unrank_state(rank)
            if distance:
                following = _move(state, self.next_tiles[rank])
                if self.distances[rank_state(following)] != distance - 1:
                    raise ValueError("Solution table route does not decrease distance.")
            for target in ADJACENCY[state.index(0)]:
                neighbor_distance = self.distances[rank_state(_move(state, target))]
                if neighbor_distance == UNKNOWN:
                    if self.is_complete:
                        raise ValueError("Complete table is missing a reachable neighbor.")
                elif abs(distance - neighbor_distance) > 1:
                    raise ValueError("Neighboring solution distances are inconsistent.")

    @classmethod
    def load(cls, path: Path) -> "SolutionDatabase":
        # Bounded reads reject oversized inputs without allocating arbitrary data.
        with Path(path).open("rb") as handle:
            data = handle.read(FILE_SIZE + 1)
        if len(data) != FILE_SIZE:
            raise ValueError("Invalid solution table file size.")
        magic, version, grid, entries, slots, checksum = HEADER.unpack(data[:HEADER.size])
        if magic != MAGIC or version != VERSION or grid != GRID_SIZE or slots != PERMUTATION_COUNT:
            raise ValueError("Unsupported solution table format, version, or dimensions.")
        payload = data[HEADER.size:]
        if hashlib.sha256(payload).digest() != checksum:
            raise ValueError("Solution table checksum mismatch.")
        database = cls(payload[:PERMUTATION_COUNT], payload[PERMUTATION_COUNT:], entries)
        database._validate_routes()
        return database

    def save(self, path: Path):
        """Atomically replace one data-only artifact; write failures propagate."""
        path = Path(path)
        payload = self.distances + self.next_tiles
        header = HEADER.pack(MAGIC, VERSION, GRID_SIZE, self.entry_count,
                             PERMUTATION_COUNT, hashlib.sha256(payload).digest())
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(header)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
