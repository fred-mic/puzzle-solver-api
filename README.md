# 8-Puzzle Solver API

This project provides a high-performance FastAPI service to solve 8-puzzles (3x3 grids). It uses an A\* search algorithm and a pre-calculated FAISS vector database to deliver solutions instantly for any valid puzzle state.

## Project Structure

-   `main.py`: The FastAPI application defining the web endpoints.
-   `puzzle_service.py`: Contains all the core business logic for solving and database management.
-   `build_db.py`: A one-time script to generate the solution database files.
-   `requirements.txt`: Python dependencies.
-   `setup.py`: Build script for the cpp-solver module
-   `cpp-solver`: C++ library that implements the A\* search algorithm for solutions to the puzzle

## Setup and Usage

### 1. Install Dependencies

It is highly recommended to use a Python virtual environment.

**Run these commands from your terminal:**

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install required packages
pip install -r requirements.txt
```
### 2. Build the module used to create solutions (C++ source files)

For fast creation of the solutions database a C++ implementation of the A\* algorithm is used to solve all the 181,440 possible combinations of puzzle states.


**Run this from your terminal:**

```bash
python setup.py build_ext --inplace
```

### 3. Build the Solution Database

Before running the server for the first time, you must generate the `puzzle_solutions.faiss` and `puzzle_solutions_metadata.pkl` files. This is a one-time, CPU-intensive process that solves all possible 181,440 valid 8-puzzles.

**Run this command from your terminal:**

```bash
python build_db.py
```

This will take several minutes to complete. You will see progress bars for the generation and solving steps.

### 4. Run the FastAPI Server

Once the database files are built, you can start the API server using Uvicorn.

```bash
uvicorn main:app --reload
```

-   `main`: The file `main.py`.
-   `app`: The `FastAPI()` object created inside `main.py`.
-   `--reload`: Enables auto-reloading so the server restarts when you change the code.

The server will be running at `http://127.0.0.1:8000`.

### 5. Interact with the API

You can now send requests to the API. You can use tools like `curl`, Postman, or any programming language. The interactive docs are also available at `http://127.0.0.1:8000/docs`.

**Example using `curl`:**

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/solve' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "state":
}'
```

**Expected Response:**

```json
{
  "solution": [
   ,
   ,
   
  ]
}
```