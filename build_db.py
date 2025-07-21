# build_db.py
from puzzle_service import PuzzleService
import time

DB_FILENAME = "puzzle_solutions"
# For a 3x3 puzzle, there are 9! / 2 = 181,440 possible states
# Generating all of them is the most robust approach.
NUM_PUZZLES_TO_GENERATE = 181440

def main():
    """This function builds and saves the complete solution database."""
    print("=== Building Large Solution Database ===")
    print("WARNING: This will take several minutes and use significant CPU.")
    
    service = PuzzleService()
    
    start_time = time.time()
    service.build_solution_database(NUM_PUZZLES_TO_GENERATE)
    build_time = time.time() - start_time
    
    print(f"\nDatabase built in {build_time:.2f} seconds")
    service.save_database(DB_FILENAME)
    print("Database generation complete.")
    print(f"Files created: {DB_FILENAME}.faiss and {DB_FILENAME}_metadata.pkl")

if __name__ == "__main__":
    main()