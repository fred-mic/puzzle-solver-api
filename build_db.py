"""Generate the compact, immutable 8-puzzle solution table offline."""
import time
from puzzle_service import DATABASE_PATH, PuzzleService
from solution_database import MAX_MOVES, REACHABLE_COUNT


def main():
    print("=== Building Immutable Solution Table with Reverse BFS ===")
    service = PuzzleService()
    start_time = time.perf_counter()
    service.build_solution_database(REACHABLE_COUNT)
    if service.database_entries != REACHABLE_COUNT:
        raise RuntimeError("Reverse BFS did not generate all 181,440 reachable states.")
    if service.database.maximum_distance != MAX_MOVES:
        raise RuntimeError("Unexpected maximum 8-puzzle solution distance.")
    service.save_database()
    print(f"\nBuilt {service.database_entries} optimal entries in {time.perf_counter() - start_time:.2f} seconds")
    print(f"Maximum distance: {service.database.maximum_distance} moves")
    print(f"Artifact: '{DATABASE_PATH}' ({DATABASE_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
