import os
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Database settings
DATABASE = {
    "sqlite": {
        "filename": "execution_tracker.db",
        "directory": "data",
        "path": str(PROJECT_ROOT / "data" / "execution_tracker.db")
    }
}

# Ensure data directory exists
os.makedirs(PROJECT_ROOT / "data", exist_ok=True) 