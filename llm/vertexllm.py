from utils import bootstrap  # This must be the first import
import os
from typing import Optional, Dict, Any
from loguru import logger
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, SafetySetting, HarmCategory, HarmBlockThreshold
from google.oauth2 import service_account

def get_safety_settings():
    """Get permissive safety settings for Vertex AI"""
    safety_config = [
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_UNSPECIFIED,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        )
    ]
    return safety_config

    # ]
    # return {
    #     HarmCategory.HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    #     HarmCategory.DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    #     HarmCategory.HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    #     HarmCategory.SEXUAL_CONTENT: HarmBlockThreshold.BLOCK_NONE,

        
    # }

class VertexLLM:
    """Interface for Google Cloud's Vertex AI Gemini service using the official SDK"""

    def __init__(self):
        self.initialize_vertex_ai()
    

    def get_credentials(self) -> service_account.Credentials:
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is required")
        return service_account.Credentials.from_service_account_file(credentials_path)



    def initialize_vertex_ai(self):
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
                credentials=self.get_credentials(),
                api_transport="rest"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI LLM: {str(e)}")
            raise
    
    async def generate_content(
        self,
        prompt: str,
        temperature: float = 0.2,
        top_p: float = 0.8,
        top_k: int = 40,
        **kwargs: Dict[str, Any]
    ) -> str:
        """
        Generate content using Vertex AI's Gemini model.
        
        Args:
            prompt: The input prompt for generation
            temperature: Controls randomness (0.0-1.0)
            top_p: Nucleus sampling parameter
            top_k: Number of highest probability tokens to consider
            **kwargs: Additional parameters for the model
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If content generation fails
        """
        try:
            logger.debug(f"Generating content with temperature={temperature}")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            # Configure generation parameters
            generation_config = GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                candidate_count=1
            )
            
            model_version = os.getenv('VERTEX_MODEL_VERSION', 'gemini-1.5-pro')
            self.model = GenerativeModel(model_version)

            # Generate content using the model with safety settings
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=get_safety_settings(),
                **kwargs
            )
            
            generated_text = response.text
            
            # Log just the response to console
            logger.info("\n" + "="*80)
            logger.info("LLM RESPONSE:")
            logger.info(generated_text)
            logger.info("="*80 + "\n")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Failed to generate content: {str(e)}")
            logger.error(f"Prompt that caused error:\n{prompt}")
            raise