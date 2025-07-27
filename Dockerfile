# Dockerfile

# Latest Python NOT RECOMMENDED for production:
FROM python:3.13-rc-slim

# Set the working directory inside the container
WORKDIR /app

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --- Stage 2: Install Dependencies ---
# Copy only the requirements file first to leverage Docker's layer caching.
# This layer will only be rebuilt if requirements.txt changes.
COPY requirements.txt .

# Install the Python dependencies
# --no-cache-dir keeps the image size smaller
RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 3: Copy Application Code ---
# Copy the rest of your application's source code into the container
COPY . .

# --- Stage 4: Expose the Port ---
# Let Docker know that the container listens on port 8000
EXPOSE 8000

# --- Stage 5: Define the Runtime Command ---
# This is the command that will run when the container starts.
# Use --host 0.0.0.0 to make the server accessible from outside the container.
# Using 'localhost' or '127.0.0.1' would only allow connections from *within* the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]