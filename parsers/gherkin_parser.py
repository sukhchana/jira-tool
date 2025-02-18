from typing import Dict, Any, List
from loguru import logger
import json
from .base_parser import BaseParser

class GherkinParser(BaseParser):
    """Parser for Gherkin scenario content"""
    
    @classmethod
    def parse(cls, content: str) -> List[Dict[str, Any]]:
        """Parse Gherkin scenarios from content"""
        try:
            # Parse JSON array, handling markdown code blocks
            scenarios = cls.parse_json_content(content)
            if not isinstance(scenarios, list):
                logger.error("Response is not a JSON array")
                return cls._create_error_scenario()
            
            # Validate and clean each scenario
            validated_scenarios = []
            for scenario in scenarios:
                if cls._validate_scenario(scenario):
                    validated_scenarios.append({
                        "name": cls._clean_text(scenario["name"]),
                        "steps": [
                            {
                                "keyword": step["keyword"],
                                "text": cls._clean_text(step["text"])
                            }
                            for step in scenario["steps"]
                            if cls._validate_step(step)
                        ]
                    })
            
            return validated_scenarios if validated_scenarios else cls._create_error_scenario()
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response:\n{content}")
            return cls._create_error_scenario()
        except Exception as e:
            logger.error(f"Failed to parse Gherkin scenarios: {str(e)}")
            logger.error(f"Content that caused error:\n{content}")
            return cls._create_error_scenario()
    
    @staticmethod
    def _validate_scenario(scenario: Dict[str, Any]) -> bool:
        """Validate a scenario has all required fields"""
        return (
            isinstance(scenario, dict) and
            "name" in scenario and
            scenario["name"] and
            "steps" in scenario and
            isinstance(scenario["steps"], list) and
            scenario["steps"]
        )
    
    @staticmethod
    def _validate_step(step: Dict[str, Any]) -> bool:
        """Validate a step has all required fields"""
        return (
            isinstance(step, dict) and
            "keyword" in step and
            step["keyword"] in ["Given", "When", "Then", "And"] and
            "text" in step and
            step["text"]
        )
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean text by removing extra whitespace"""
        if not text:
            return text
        return ' '.join(text.split())
    
    @staticmethod
    def _create_error_scenario() -> List[Dict[str, Any]]:
        """Create an error scenario"""
        return [{
            "name": "Error Scenario",
            "steps": [
                {
                    "keyword": "Given",
                    "text": "Error parsing scenarios"
                }
            ]
        }] 