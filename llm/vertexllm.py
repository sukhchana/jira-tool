from utils import bootstrap  # This must be the first import
import os
import aiohttp
import json
from typing import Optional, Dict, Any
from fastapi import HTTPException
from loguru import logger

class VertexLLM:
    """Service class for interacting with Google's Vertex AI LLM (Gemini) via REST API"""
    
    def __init__(self):
        """Initialize Vertex AI connection"""
        try:
            logger.info("Initializing Vertex AI connection")
            
            # Get configuration from environment variables
            self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            
            if not self.project_id:
                raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")

            # Base URL for Vertex AI API
            self.base_url = f"https://{self.location}-aiplatform.googleapis.com/v1"
            
            # Get credentials
            from google.oauth2 import service_account
            from google.auth.transport import requests

            credentials = service_account.Credentials.from_service_account_file(
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            # Store auth header
            auth_req = requests.Request()
            credentials.refresh(auth_req)
            self.headers = {
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json"
            }
            
            logger.info("Successfully initialized Vertex AI connection")

        except Exception as e:
            error_msg = f"Failed to initialize Vertex AI: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )

    async def generate_content(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 1024,
        temperature: float = 0.2,
        top_p: float = 0.8,
        top_k: int = 40
    ) -> str:
        """Generate content using Vertex AI REST API"""
        try:
            logger.debug(f"Generating content with prompt length: {len(prompt)}")
            
            # Endpoint for text generation
            url = f"{self.base_url}/projects/{self.project_id}/locations/{self.location}/publishers/google/models/gemini-1.5-pro:generateContent"
            
            # Prepare request payload
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "generation_config": {
                    "max_output_tokens": max_output_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "top_k": top_k
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract generated text from response
                        try:
                            generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                            logger.info("Successfully generated content from Vertex AI")
                            return generated_text
                        except (KeyError, IndexError) as e:
                            raise ValueError(f"Unexpected response format: {str(e)}")
                    else:
                        error_msg = (
                            f"Vertex AI API Error:\n"
                            f"URL: {url}\n"
                            f"Status Code: {response.status}\n"
                            f"Response: {await response.text()}"
                        )
                        raise HTTPException(
                            status_code=response.status,
                            detail=error_msg
                        )

        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM generation failed: {str(e)}"
            )

    async def refresh_token(self):
        """Refresh the authentication token"""
        try:
            from google.oauth2 import service_account
            from google.auth.transport import requests

            credentials = service_account.Credentials.from_service_account_file(
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            auth_req = requests.Request()
            credentials.refresh(auth_req)
            self.headers["Authorization"] = f"Bearer {credentials.token}"
            
            logger.debug("Successfully refreshed Vertex AI token")
            
        except Exception as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to refresh authentication token: {str(e)}"
            ) 