# build_db.py

from puzzle_service import PuzzleService, DB_FILENAME_BASE
import time
import math

def main():
    """
    Builds the complete solution database and saves the files locally.
    """
    TOTAL_POSSIBLE_STATES = math.factorial(9) // 2 
    
    print("=== Building Complete Solution Database Locally ===")
    service = PuzzleService()
    
    start_time = time.time()
    # This function generates all states and solves them, populating the
    # service's in-memory database attributes.
    service.build_solution_database(TOTAL_POSSIBLE_STATES)
    build_time = time.time() - start_time
    
    print(f"\nDatabase built in {build_time:.2f} seconds")
    
    # Now, call the refactored save_database method to write the
    # in-memory database to local files.
    service.save_database()
    
    print("\nDatabase generation complete.")
    print(f"Files created: '{DB_FILENAME_BASE}.faiss' and '{DB_FILENAME_BASE}_metadata.pkl'")


if __name__ == "__main__":
    main()