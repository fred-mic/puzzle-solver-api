# Use the same supported stable Python release and OS in both stages.
FROM python:3.13-slim-bookworm AS builder
WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-build.txt ./
RUN python -m pip install --no-cache-dir -r requirements-build.txt \
    && python -m pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

COPY setup.py pyproject.toml MANIFEST.in VERSION ./
COPY cpp-solver/src/ ./cpp-solver/src/
RUN python -m pip wheel --no-cache-dir --no-deps --no-build-isolation . -w /wheels

FROM python:3.13-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# Only the C++ runtime library is needed; no compiler or build tools.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app \
    && python -m venv /opt/venv

COPY requirements.txt ./
# Mount wheels for installation without retaining them in an image layer.
RUN --mount=from=builder,source=/wheels,target=/wheels \
    python -m pip install --no-cache-dir --no-index --find-links=/wheels --no-deps \
        -r requirements.txt cpp_solver \
    && python -m pip check \
    && python -c "import cpp_solver; assert cpp_solver.solve([1,2,3,4,5,6,7,0,8]) == [(2, 2)]"

COPY main.py config.py puzzle_service.py solution_database.py build_db.py puzzle_solutions.bin ./
USER app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
