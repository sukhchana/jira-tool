from typing import Dict, Any, Optional, List
from loguru import logger
from .base_parser import BaseParser
import json

class TechnicalTaskParser(BaseParser):
    """Parser for technical tasks"""
    
    @classmethod
    def parse_from_response(cls, response: str) -> List[Dict[str, Any]]:
        """Extract and parse all technical tasks from a response"""
        try:
            # Parse JSON array, handling markdown code blocks
            tasks = cls.parse_json_content(response)
            if not isinstance(tasks, list):
                logger.error("Response is not a JSON array")
                return []
                
            parsed_tasks = []
            for i, task in enumerate(tasks, 1):
                try:
                    parsed_task = cls._validate_task(task)
                    if parsed_task:
                        parsed_tasks.append(parsed_task)
                    else:
                        logger.warning(f"Failed to validate technical task {i}")
                except Exception as e:
                    logger.error(f"Failed to parse technical task {i}: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(parsed_tasks)} technical tasks")
            return parsed_tasks
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response:\n{response}")
            return []
        except Exception as e:
            logger.error(f"Failed to parse technical tasks from response: {str(e)}")
            return []

    @classmethod
    def _validate_task(cls, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and clean up a technical task"""
        try:
            # Validate required fields
            required_fields = [
                "title", "description", "technical_domain", 
                "implementation_approach", "performance_impact",
                "scalability_considerations", "monitoring_needs",
                "testing_requirements"
            ]
            if not all(field in task for field in required_fields):
                missing = [f for f in required_fields if f not in task]
                logger.error(f"Missing required fields: {missing}")
                return None

            # Validate implementation approach fields
            impl_fields = ["architecture", "apis", "database", "security"]
            impl_approach = task.get("implementation_approach", {})
            if not all(field in impl_approach for field in impl_fields):
                missing = [f for f in impl_fields if f not in impl_approach]
                logger.error(f"Missing implementation approach fields: {missing}")
                return None

            # Clean and validate fields
            validated = {
                "type": "Technical Task",
                "title": cls._clean_text(task["title"]),
                "description": cls._clean_text(task["description"]),
                "technical_domain": cls._clean_text(task["technical_domain"]),
                "complexity": cls._validate_enum(
                    task.get("complexity", "Medium"),
                    ["Low", "Medium", "High"],
                    "Medium"
                ),
                "business_value": cls._validate_enum(
                    task.get("business_value", "Medium"),
                    ["Low", "Medium", "High"],
                    "Medium"
                ),
                "story_points": cls._parse_story_points(task.get("story_points", "3")),
                "required_skills": task.get("required_skills", []),
                "suggested_assignee": task.get("suggested_assignee", "Unassigned"),
                "dependencies": task.get("dependencies", []),
                "implementation_approach": {
                    "architecture": cls._clean_text(impl_approach["architecture"]),
                    "apis": cls._clean_text(impl_approach["apis"]),
                    "database": cls._clean_text(impl_approach["database"]),
                    "security": cls._clean_text(impl_approach["security"])
                },
                "acceptance_criteria": task.get("acceptance_criteria", []),
                "performance_impact": cls._clean_text(task["performance_impact"]),
                "scalability_considerations": cls._clean_text(task["scalability_considerations"]),
                "monitoring_needs": cls._clean_text(task["monitoring_needs"]),
                "testing_requirements": cls._clean_text(task["testing_requirements"])
            }

            return validated

        except Exception as e:
            logger.error(f"Error validating technical task: {str(e)}")
            return None

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Clean text by removing extra whitespace"""
        if not text:
            return text
        return ' '.join(text.split())

    @classmethod
    def _parse_story_points(cls, points_text: str) -> int:
        """Parse and validate story points"""
        try:
            points = int(str(points_text))
            valid_points = [1, 2, 3, 5, 8, 13]
            return min(valid_points, key=lambda x: abs(x - points))
        except (ValueError, TypeError):
            return 3  # Default to 3 if parsing fails

    @classmethod
    def _validate_enum(cls, value: str, valid_values: List[str], default: str) -> str:
        """Validate enum values"""
        clean_value = value.strip().capitalize()
        return clean_value if clean_value in valid_values else default

    @classmethod
    def _create_error_task(cls, error_msg: str) -> Dict[str, Any]:
        """Create an error task with minimal required fields"""
        return {
            "type": "Technical Task",
            "title": "Error parsing technical task",
            "description": f"Failed to parse: {error_msg}",
            "technical_domain": "Unknown",
            "required_skills": [],
            "suggested_assignee": "Unassigned",
            "complexity": "Medium",
            "business_value": "Medium",
            "story_points": 3,
            "dependencies": [],
            "implementation_approach": {
                "architecture": "Error parsing task",
                "apis": "Error parsing task",
                "database": "Error parsing task",
                "security": "Error parsing task"
            },
            "acceptance_criteria": [],
            "performance_impact": "Error parsing task",
            "scalability_considerations": "Error parsing task",
            "monitoring_needs": "Error parsing task",
            "testing_requirements": "Error parsing task"
        } 