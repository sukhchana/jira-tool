import asyncio
import os
from typing import Dict, Any

from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
from loguru import logger

# Only import bootstrap when not running directly
if __name__ != "__main__":
    pass


class GenAILLM:
    """Interface for Google's Generative AI service using google-genai package"""

    def __init__(self):
        self.initialize_genai()

    def initialize_genai(self):
        """Initialize Google GenAI client with Vertex AI settings"""
        try:
            # Get configuration from environment variables
            project_id = os.getenv('GCP_PROJECT_ID')
            location = os.getenv('VERTEX_LOCATION', 'us-central1')

            if not project_id:
                raise ValueError("GCP_PROJECT_ID environment variable is required")

            # Initialize the Google GenAI client with Vertex AI settings
            self.client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location
            )
            logger.info(f"Google GenAI client initialized with project: {project_id}, location: {location}")

        except Exception as e:
            logger.error(f"Failed to initialize Google GenAI: {str(e)}")
            raise

    async def generate_content_with_search(
            self,
            prompt: str,
            temperature: float = 0.2,
            **kwargs: Dict[str, Any]
    ) -> str:
        """
        Generate content using Gemini with Google Search grounding.
        
        Args:
            prompt: The input prompt for generation
            temperature: Controls randomness (0.0-1.0)
            **kwargs: Additional parameters for the model
            
        Returns:
            Generated text response grounded in Google Search results
            
        Raises:
            Exception: If content generation fails
        """
        try:
            logger.debug(f"Generating content with Google Search grounding")
            logger.debug(f"Prompt length: {len(prompt)} characters")

            # Get model ID from environment or use default
            model_id = os.getenv('VERTEX_MODEL_VERSION', 'gemini-2.0-flash')
            logger.debug(f"Using model: {model_id}")

            # Configure Google Search tool
            google_search_tool = Tool(
                google_search=GoogleSearch()
            )

            # Generate content using the model with search tool
            response = self.client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=temperature,
                    tools=[google_search_tool],
                    response_modalities=["TEXT"],
                ),
                **kwargs
            )

            # Log if we have grounding metadata
            if hasattr(response.candidates[0], 'grounding_metadata') and response.candidates[0].grounding_metadata:
                logger.debug("Response includes grounding metadata")
                metadata = response.candidates[0].grounding_metadata
                if hasattr(metadata, 'search_entry_point') and metadata.search_entry_point:
                    logger.debug("Response includes search entry point")
                    if hasattr(metadata.search_entry_point, 'rendered_content'):
                        logger.debug(f"Search content available")

            # Get text from all parts
            text_parts = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text'):
                    text_parts.append(part.text)

            result = "\n".join(text_parts)
            logger.debug(f"Generated response length: {len(result)} characters")
            return result

        except Exception as e:
            logger.error(f"Failed to generate content with search: {str(e)}")
            logger.error(f"Prompt that caused error:\n{prompt}")
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
        Generate content using Google's Gemini model via genai package.
        
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

            # Get model ID from environment or use default
            model_id = os.getenv('VERTEX_MODEL_VERSION', 'gemini-2.0-flash')
            logger.debug(f"Using model: {model_id}")

            # Generate content using the new client interface
            response = self.client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    candidate_count=1
                ),
                **kwargs
            )

            # Check response format and extract text
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                text_parts = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text'):
                        text_parts.append(part.text)
                return "\n".join(text_parts)
            else:
                raise ValueError("Unexpected response format from the API")

        except Exception as e:
            logger.error(f"Failed to generate content: {str(e)}")
            logger.error(f"Prompt that caused error:\n{prompt}")
            raise


if __name__ == "__main__":
    # Configure logging
    logger.add("genaillm_test.log", rotation="500 MB")


    async def test_llm():
        try:
            print("Initializing GenAI LLM...")
            llm = GenAILLM()

            # Test regular generation
            print("\nTesting regular generation:")
            response = await llm.generate_content(
                "Tell me a short joke about programming",
                temperature=0.7
            )
            print(response)

            # Test generation with search
            print("\nTesting generation with Google Search grounding:")
            response = await llm.generate_content_with_search(
                "When is the next total solar eclipse in the United States?",
                temperature=0.0
            )
            print(response)
            
            # Example of how to access grounding metadata
            print("\nRunning test with grounding metadata extraction:")
            test_prompt = "What are the latest developments in quantum computing?"
            print(f"Prompt: {test_prompt}")
            
            # Direct client access for metadata demo
            direct_response = llm.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=test_prompt,
                config=GenerateContentConfig(
                    temperature=0.0,
                    tools=[Tool(google_search=GoogleSearch())],
                    response_modalities=["TEXT"],
                )
            )
            
            # Print the response
            for part in direct_response.candidates[0].content.parts:
                if hasattr(part, 'text'):
                    print(part.text)
            
            # Access grounding metadata if available
            if hasattr(direct_response.candidates[0], 'grounding_metadata') and direct_response.candidates[0].grounding_metadata:
                metadata = direct_response.candidates[0].grounding_metadata
                if hasattr(metadata, 'search_entry_point') and metadata.search_entry_point:
                    if hasattr(metadata.search_entry_point, 'rendered_content'):
                        print("\nGrounding Metadata (Search Content):")
                        print(metadata.search_entry_point.rendered_content)

        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            print(f"Error: {str(e)}")
            raise


    # Run the test
    print("Starting GenAI LLM test...")
    print("Make sure you have set these environment variables:")
    print("- GCP_PROJECT_ID")
    print("- VERTEX_LOCATION (optional, defaults to us-central1)")
    print("- VERTEX_MODEL_VERSION (optional, defaults to gemini-2.0-flash)")
    print("\nRunning tests...")

    asyncio.run(test_llm())
