from dotenv import load_dotenv
import os
from pathlib import Path
from loguru import logger

def load_environment():
    """
    Load environment variables from .env file
    Returns True if successful, False otherwise
    """
    try:
        # Get the project root directory (where .env should be)
        project_root = Path(__file__).parent.parent
        env_path = project_root / '.env'
        
        # Check if .env exists
        if not env_path.exists():
            logger.error(f".env file not found at {env_path}")
            return False
            
        # Load the .env file
        load_dotenv(env_path)
        
        # Verify required variables
        required_vars = [
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_LOCATION"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
            
        logger.info("Successfully loaded environment variables")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load environment variables: {str(e)}")
        return False 