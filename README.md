# 8-Puzzle Solver API

This project provides a FastAPI service to solve 8-puzzles (3x3 grids). One
reverse breadth-first search (BFS) precomputes distances and next moves for all
181,440 reachable states. A compact immutable table reconstructs optimal paths
on demand, without a vector database, object deserialization, or request-time
cache mutation.

## Project Structure

-   `main.py`: The FastAPI application defining the web endpoints.
-   `puzzle_service.py`: Contains all the core business logic for solving and database management.
-   `build_db.py`: Builds the compact solution table offline using reverse BFS.
-   `solution_database.py`: Versioned binary format, permutation ranking, validation, and read-only lookup.
-   `puzzle_solutions.bin`: The generated distance/next-move table.
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
Before starting the server, copy `.env.template` to `.env`
and set `API_SECRET_TOKEN` to a strong random secret. You can generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Keep `.env` private and out of version control. Alternatively, set
`API_SECRET_TOKEN` directly in the server's environment.

### 2. Build the module used to create solutions (C++ source files)

The `cpp_solver` extension remains required when importing the service,
including from the API and `build_db.py`. Build it in the same Python environment
used to run them. Generation uses reverse BFS and never invokes native A\*.
The native solver is used only for valid states missing from an absent or partial
in-memory table; its results are not cached. With the complete table, unsolvable
permutations are rejected without native search. Import errors fail immediately
with build instructions; there is no Python solver fallback.


**Run this from your terminal:**

```bash
python setup.py build_ext --inplace
# Verify that the native module imports and solves a one-move puzzle.
python -c "import cpp_solver; print(cpp_solver.solve([1,2,3,4,5,6,7,0,8]))"
```

### 3. Build the Solution Database

Generate or atomically replace `puzzle_solutions.bin` with the following command.
One reverse BFS records shortest-path parents, then encodes distance and next-tile
bytes by permutation rank. Full paths are reconstructed only when requested.
Traversal is O(V + E); no per-state A\* searches or full-path dictionaries are
needed. The offline builder does not require an API authentication secret.

**Run this command from your terminal:**

```bash
python build_db.py
```

The builder checks all 181,440 reachable entries and the maximum distance of
31 moves. The single artifact is 725,810 bytes (about 0.7 MiB): a 50-byte header
with format/version/dimensions/count/checksum, followed by two 362,880-byte arrays.
Each permutation has one distance byte and one next-tile byte; 255 marks unknown
entries and the goal's lack of a next move.

Loading uses a bounded read, validates the header and SHA-256 checksum, and checks
legal descending routes and neighboring distances before publishing immutable
`bytes`. Missing, corrupt, or unsupported artifacts fail server startup rather
than leaving partially loaded data. The default path is relative to the source
file, not the process's working directory. Save failures propagate and leave the
previous file intact via atomic replacement.

Old artifacts are not imported or migrated; rebuild them with `python build_db.py`.
SHA-256 detects corruption, not malicious replacement by someone who can rewrite
the file. Deploy the generated artifact as read-only from a trusted build source.

Requests read one immutable snapshot and return fresh path lists. They never
add entries, change stored paths, or write files. A complete table eliminates
online search; native results for partial-table misses remain uncached.

### 4. Run the FastAPI Server

Once `puzzle_solutions.bin` is built, you can start the API server using Uvicorn.

```bash
uvicorn main:app --reload
```

-   `main`: The file `main.py`.
-   `app`: The `FastAPI()` object created inside `main.py`.
-   `--reload`: Enables auto-reloading so the server restarts when you change the code.

The server will be running at `http://127.0.0.1:8000`.

### 5. Interact with the API

You can now send requests to the API. You can use tools like `curl`, Postman, or any programming language. The interactive docs are also available at `http://127.0.0.1:8000/docs`.

`POST /solve` requires an `Authorization: Bearer <token>` header. Missing,
incorrect, or malformed credentials receive `401 Unauthorized` with
`WWW-Authenticate: Bearer`. The health check (`GET /`) remains public.

This shared secret is intended for trusted service-to-service clients. Do not
embed it in a React app or other distributed browser code; use individual
identity-based credentials for public clients. CORS is not access control. Use
HTTPS when deploying the API.

**Example using `curl`:**

Set `API_SECRET_TOKEN` in your client shell to the same secret configured on the
server. The server's `.env` loading does not export it to your shell.

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/solve' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${API_SECRET_TOKEN}" \
  -d '{"state": [1,2,3,4,5,6,7,0,8]}'
```

**Expected Response:**

```json
{"solution":[[1,2,3,4,5,6,7,0,8],[1,2,3,4,5,6,7,8,0]]}
```

## Authentication Tests

Install the test dependencies and run the authentication regression suite:

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -p 'test_authentication.py' -v
```

The tests use a temporary test token and mock database loading and solving; no
real API secret or solution artifacts are needed. The required native extension
must still be built as described in step 2 before importing the API.

## Native Backend Tests

These isolated unit tests mock native imports to verify successful delegation,
result conversion, non-mutating misses, and fail-fast errors for missing or broken modules:

```bash
python -m unittest discover -s tests -p 'test_native_backend.py' -v
```

The native backend unit tests do not require a compiled extension.

## Database Generation Tests

```bash
python -m unittest discover -s tests -p 'test_database_generation.py' -v
```

These tests verify legal shortest paths against an independent BFS, no A\* calls
during generation, exact limits, deterministic encoding, clean rebuilds, safe
loading, fresh paths, and non-mutating misses. They mock the native import and do
not require a compiled extension.

## Storage Format Tests

```bash
python -m unittest discover -s tests -p 'test_solution_database.py' -v
```

These standard-library-only tests cover permutation ranking, immutable data,
bounded parsing, corrupt headers/checksums/routes, and atomic write failures.

Run all tests after building the native extension:

```bash
python -m unittest discover -s tests -v
```
