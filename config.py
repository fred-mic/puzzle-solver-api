# /puzzle-solver-api/config.py

import os
from dotenv import load_dotenv

# --- The Core Logic ---
# load_dotenv() will automatically find and load a .env file in the same directory.
# Where there is no .env file, this function will simply do nothing.
# This makes the code seamlessly work both locally and in the cloud.
load_dotenv()

# --- Application Secrets & Configuration ---

# API authentication bearer token
API_SECRET_TOKEN = os.getenv("API_SECRET_TOKEN")
if not API_SECRET_TOKEN:
    raise ValueError("FATAL: API_SECRET_TOKEN environment variable not set.")
