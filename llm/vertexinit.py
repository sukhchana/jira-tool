import os
import vertexai
from google.oauth2 import service_account
from loguru import logger

def get_credentials() -> service_account.Credentials:
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is required")
    return service_account.Credentials.from_service_account_file(credentials_path)

def initialize_vertex_ai():
    """Initialize Vertex AI client with project and endpoint settings"""
    try:
        # Get configuration from environment variables
        project_id = os.getenv('GCP_PROJECT_ID')
        location = os.getenv('VERTEX_LOCATION', 'us-central1')
        endpoint = os.getenv('VERTEX_API_ENDPOINT', f'{location}-aiplatform.googleapis.com')

        if not project_id:
            raise ValueError("GCP_PROJECT_ID environment variable is required")

        # Initialize Vertex AI with specific configurations
        vertexai.init(
            project=project_id,
            location=location,
            api_endpoint=endpoint,
            credentials=get_credentials(),
            api_transport="rest"
        )

    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI LLM: {str(e)}")
        raise