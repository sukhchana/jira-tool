import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Get the project root directory
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'

# Load environment variables immediately when this module is imported
if not env_path.exists():
    print(f"ERROR: .env file not found at {env_path}")
    sys.exit(1)

load_dotenv(env_path)

# Verify critical environment variables
required_vars = [
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_LOCATION"
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)
