from typing import Dict, Any

from loguru import logger

from llm.vertexllm import VertexLLM


class BaseInterpreter:
    """Base class for all revision interpreters"""

    def __init__(self):
        """Initialize the interpreter with LLM"""
        self.llm = VertexLLM()

    async def generate_interpretation(self, prompt: str) -> str:
        """Generate interpretation using LLM"""
        try:
            return await self.llm.generate_content(
                prompt,
                temperature=0.2,
                top_p=0.8,
                top_k=40
            )
        except Exception as e:
            logger.error(f"Failed to generate interpretation: {str(e)}")
            raise

    def format_ticket_data(self, ticket_data: Dict[str, Any]) -> str:
        """Format ticket data for prompts"""
        return "\n".join(f"{key}: {value}" for key, value in ticket_data.items())
