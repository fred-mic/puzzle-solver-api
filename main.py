# main.py
from fastapi import FastAPI, HTTPException, Security
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from puzzle_service import PuzzleService
from contextlib import asynccontextmanager
import config


# --- Security Setup ---
# This tells FastAPI to look for an "Authorization: Bearer <token>" header
bearer_scheme = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    """
    A dependency that verifies the provided bearer token.
    If the token is invalid, it raises a 401 Unauthorized error.
    """

    if credentials.scheme != "Bearer" or credentials.credentials != config.API_SECRET_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


#    For development, this is your React app's address.
origins = [
    "http://localhost:5173",
    "http://localhost:3000", # Common alternative React dev port
    "http://127.0.0.1:5173",
]

# --- Pydantic Models for API Data Validation ---
class PuzzleState(BaseModel):
    state: List[int]

class SolutionPath(BaseModel):
    solution: List[List[int]]

# --- FastAPI Application Setup ---

@asynccontextmanager
async def lifespan(app):
    print("Server starting up...")
    puzzle_service.load_database()
    yield
    print("Server shutting down...")

app = FastAPI(
    title="8-Puzzle Solver API",
    description="An API to solve 8-puzzles (3x3 grid) using a pre-calculated pattern database.",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)


# Create a single, shared instance of our service
# This instance will be populated at startup.
puzzle_service = PuzzleService()

# --- API Endpoints ---
@app.get("/", summary="Health Check")
def read_root():
    """A simple health check endpoint to confirm the API is running."""
    return {
        "status": "ok",
        "database_entries": puzzle_service.index.ntotal if puzzle_service.index else 0,
        "message": "Welcome to the Puzzle Solver API!"
    }


@app.post("/solve", response_model=SolutionPath, summary="Solve a Puzzle")
async def solve_puzzle(puzzle: PuzzleState):
    """
    Receives a puzzle state and returns the optimal solution path.

    - **state**: A list of 9 integers representing the grid, with 0 as the empty space.
    """
    if len(puzzle.state) != 9:
        raise HTTPException(status_code=400, detail="Invalid puzzle state. Must contain 9 integers.")
    
    # Convert list to tuple for the service layer
    query_state_tuple = tuple(puzzle.state)
    
    solution_path = puzzle_service.solve_using_database(query_state_tuple)
    
    if not solution_path:
        raise HTTPException(status_code=404, detail="No solution could be found for the given puzzle state.")

    # Convert tuples back to lists for the JSON response
    solution_path_lists = [list(state) for state in solution_path]
    
    return {"solution": solution_path_lists}