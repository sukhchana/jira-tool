import json
from typing import Dict, Any

from loguru import logger

from .base_parser import BaseParser


class ResearchSummaryParser(BaseParser):
    """Parser for research summary content"""

    @classmethod
    def parse(cls, content: str) -> Dict[str, Any]:
        """Parse research summary from content"""
        try:
            # Handle empty content
            if not content or not content.strip():
                logger.debug("Empty content provided, returning default research summary")
                return cls._create_default_summary()

            # Parse JSON response, handling Markdown code blocks
            research_data = cls.parse_json_content(content)
            if not research_data:
                logger.debug("No JSON content found, returning default research summary")
                return cls._create_default_summary()

            # Validate required fields
            required_fields = ["pain_points", "success_metrics", "similar_implementations", "modern_approaches"]
            if not all(field in research_data for field in required_fields):
                missing = [f for f in required_fields if f not in research_data]
                logger.error(f"Missing required fields in research summary: {missing}")
                return cls._create_default_summary()

            # Clean and return the data
            return {
                "pain_points": cls._clean_field(research_data["pain_points"]),
                "success_metrics": cls._clean_field(research_data["success_metrics"]),
                "similar_implementations": cls._clean_field(research_data["similar_implementations"]),
                "modern_approaches": cls._clean_field(research_data["modern_approaches"])
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response:\n{content}")
            return cls._create_default_summary()
        except Exception as e:
            logger.error(f"Failed to parse research summary: {str(e)}")
            logger.error(f"Content that caused error:\n{content}")
            return cls._create_default_summary()

    @classmethod
    def _clean_field(cls, field_value: Any) -> str:
        """Clean a field value that could be either a string or a list"""
        if isinstance(field_value, list):
            # Join list items with newlines and clean each item
            return "\n".join(cls._clean_text(item) for item in field_value if item)
        return cls._clean_text(field_value)

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean text by removing extra whitespace and Markdown formatting"""
        if not text:
            return ""
        # Remove markdown bold markers
        cleaned = text.replace("**", "")
        # Clean whitespace
        return ' '.join(cleaned.split())

    @staticmethod
    def _create_default_summary() -> Dict[str, str]:
        """Create a default research summary when research tasks are disabled"""
        return {
            "pain_points": "Research tasks disabled",
            "success_metrics": "Research tasks disabled",
            "similar_implementations": "Research tasks disabled",
            "modern_approaches": "Research tasks disabled"
        }

    @staticmethod
    def _create_error_summary() -> Dict[str, str]:
        """Create an error research summary"""
        return {
            "pain_points": "Error parsing research summary",
            "success_metrics": "Error parsing research summary",
            "similar_implementations": "Error parsing research summary",
            "modern_approaches": "Error parsing research summary"
        }
