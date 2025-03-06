import os
from typing import Optional, Any
from loguru import logger

# Import LLM implementations
from .vertex_llm import VertexLLM
from .anthropic_llm import AnthropicLLM

# Import metrics tracking
from services.metrics_service import track_llm_request


class TrackedLLMService:
    """Wrapper for LLM service that tracks metrics"""
    
    def __init__(self, llm_service, model_name: str):
        """Initialize with the LLM service to wrap"""
        self.llm_service = llm_service
        self.model_name = model_name
        
    async def generate_content(self, prompt: str, **kwargs) -> str:
        """Generate content from a prompt, tracking metrics"""
        return await track_llm_request(
            model=self.model_name,
            func=self.llm_service.generate_content,
            prompt=prompt,
            **kwargs
        )
    
    # Pass through any other methods
    def __getattr__(self, name):
        return getattr(self.llm_service, name)


def get_llm_service() -> Any:
    """
    Factory function to get the appropriate LLM service based on environment
    
    Returns:
        An instance of an LLM service
    """
    # Determine which LLM service to use based on environment variables
    llm_provider = os.getenv("LLM_PROVIDER", "vertex").lower()
    
    if llm_provider == "vertex":
        model_name = os.getenv("VERTEX_MODEL_VERSION", "gemini-1.5-pro")
        llm_service = VertexLLM()
        logger.info(f"Using Vertex AI LLM service with model: {model_name}")
    elif llm_provider == "anthropic":
        model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        llm_service = AnthropicLLM()
        logger.info(f"Using Anthropic LLM service with model: {model_name}")
    else:
        # Default to Vertex
        model_name = os.getenv("VERTEX_MODEL_VERSION", "gemini-1.5-pro")
        llm_service = VertexLLM()
        logger.warning(f"Unknown LLM provider: {llm_provider}, defaulting to Vertex AI")
    
    # Wrap with metrics tracking
    return TrackedLLMService(llm_service, model_name) 