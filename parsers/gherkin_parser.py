import json
from typing import Dict, Any, List

from loguru import logger

from utils.config import settings
from .base_parser import BaseParser


class GherkinParser(BaseParser):
    """Parser for Gherkin scenarios"""

    @classmethod
    def parse(cls, content: str) -> List[Dict[str, Any]]:
        """Parse Gherkin scenarios from content"""
        # If Gherkin scenario generation is disabled, return empty list
        if not settings.ENABLE_GHERKIN_SCENARIOS:
            return []

        try:
            # Parse JSON array of scenarios
            scenarios = cls.parse_json_content(content)
            if not isinstance(scenarios, list):
                logger.error("Response is not a JSON array")
                return []

            # Validate and clean each scenario
            validated_scenarios = []
            for scenario in scenarios:
                if cls._validate_scenario(scenario):
                    validated_scenarios.append({
                        "name": cls._clean_text(scenario["name"]),
                        "steps": [
                            {
                                "keyword": step["keyword"].strip(),
                                "text": cls._clean_text(step["text"])
                            }
                            for step in scenario.get("steps", [])
                            if isinstance(step, dict) and "keyword" in step and "text" in step
                        ]
                    })

            return validated_scenarios

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response:\n{content}")
            return []
        except Exception as e:
            logger.error(f"Failed to parse Gherkin scenarios: {str(e)}")
            logger.error(f"Content that caused error:\n{content}")
            return []

    @staticmethod
    def _validate_scenario(scenario: Dict[str, Any]) -> bool:
        """Validate a scenario has all required fields"""
        if not isinstance(scenario, dict):
            return False

        # Check required fields
        if "name" not in scenario or not scenario["name"]:
            return False

        # Check steps
        steps = scenario.get("steps", [])
        if not isinstance(steps, list) or not steps:
            return False

        # Validate each step
        for step in steps:
            if not isinstance(step, dict):
                return False
            if "keyword" not in step or "text" not in step:
                return False
            if not step["keyword"] or not step["text"]:
                return False

        return True

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean text by removing extra whitespace"""
        if not text:
            return text
        return text.strip()
