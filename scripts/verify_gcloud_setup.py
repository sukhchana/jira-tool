import os
from google.oauth2 import service_account
from google.cloud import aiplatform
import vertexai

def verify_gcloud_setup():
    """Verify Google Cloud configuration"""
    print("Checking Google Cloud setup...")
    
    # Check environment variables
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    
    print(f"\nEnvironment Variables:")
    print(f"Project ID: {project_id}")
    print(f"Credentials Path: {credentials_path}")
    print(f"Location: {location}")
    
    # Verify credentials file exists
    if not os.path.exists(credentials_path):
        print(f"\nERROR: Credentials file not found at {credentials_path}")
        return False
    
    try:
        # Try to load credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        print("\nSuccessfully loaded credentials")
        
        # Initialize Vertex AI
        vertexai.init(
            project=project_id,
            location=location,
            credentials=credentials_path
        )
        print("Successfully initialized Vertex AI")
        
        # Try to access the model
        model = vertexai.preview.generative_models.GenerativeModel("gemini-1.5-pro")
        print("Successfully accessed Gemini model")
        
        print("\nAll checks passed! Google Cloud is properly configured.")
        return True
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        return False

if __name__ == "__main__":
    verify_gcloud_setup() 