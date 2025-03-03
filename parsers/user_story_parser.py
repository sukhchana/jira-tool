import json
from typing import Dict, Any, List, Optional

from loguru import logger

from .base_parser import BaseParser


class UserStoryParser(BaseParser):
    """Parser for user stories"""

    @classmethod
    def parse_from_response(cls, response: str) -> List[Dict[str, Any]]:
        """Extract and parse all user stories from a response"""
        try:
            # Parse JSON array, handling Markdown code blocks
            stories = cls.parse_json_content(response)
            if not isinstance(stories, list):
                logger.error("Response is not a JSON array")
                return [cls._create_error_story("Response is not a JSON array")]

            parsed_stories = []
            for i, story in enumerate(stories, 1):
                try:
                    parsed_story = cls._validate_story(story)
                    if parsed_story:
                        parsed_stories.append(parsed_story)
                    else:
                        logger.warning(f"Failed to validate user story {i}")
                        parsed_stories.append(cls._create_error_story(f"Failed to validate user story {i}"))
                except Exception as e:
                    logger.error(f"Failed to parse user story {i}: {str(e)}")
                    parsed_stories.append(cls._create_error_story(f"Failed to parse user story {i}: {str(e)}"))
                    continue

            logger.info(f"Successfully parsed {len(parsed_stories)} user stories")
            return parsed_stories

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response:\n{response}")
            return [cls._create_error_story(f"Failed to parse JSON response: {str(e)}")]
        except Exception as e:
            logger.error(f"Failed to parse user stories from response: {str(e)}")
            return [cls._create_error_story(f"Failed to parse user stories from response: {str(e)}")]

    @classmethod
    def _validate_story(cls, story: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and clean up a user story"""
        try:
            # Validate required fields
            required_fields = ["title", "description", "technical_domain"]
            if not all(field in story for field in required_fields):
                missing = [f for f in required_fields if f not in story]
                logger.error(f"Missing required fields: {missing}")
                return None

            # Handle description format
            description = story["description"]
            if isinstance(description, str):
                # Parse string description into structured format
                # Expected format: "As a [role], I want [goal], so that [benefit]"
                try:
                    parts = description.split(", ")
                    role = parts[0].replace("As a ", "").replace("As an ", "")
                    goal = parts[1].replace("I want ", "")
                    benefit = parts[2].replace("so that ", "")

                    description = {
                        "role": role,
                        "goal": goal,
                        "benefit": benefit,
                        "formatted": description
                    }
                except Exception as e:
                    logger.error(f"Failed to parse description string: {str(e)}")
                    return None
            elif not isinstance(description, dict):
                logger.error("Description must be either a string or dictionary")
                return None

            # Clean and validate fields
            validated = {
                "type": "User Story",
                "title": cls._clean_text(story["title"]),
                "description": description,
                "technical_domain": cls._clean_text(story["technical_domain"]),
                "complexity": cls._validate_enum(
                    story.get("complexity", "Medium"),
                    ["Low", "Medium", "High"],
                    "Medium"
                ),
                "business_value": cls._validate_enum(
                    story.get("business_value", "Medium"),
                    ["Low", "Medium", "High"],
                    "Medium"
                ),
                "story_points": cls._parse_story_points(story.get("story_points", "3")),
                "required_skills": story.get("required_skills", []),
                "suggested_assignee": story.get("suggested_assignee", "Unassigned"),
                "dependencies": story.get("dependencies", []),
                "acceptance_criteria": story.get("acceptance_criteria", []),
                "implementation_notes": {
                    "technical_considerations": story.get("implementation_notes", {}).get("technical_considerations",
                                                                                          ""),
                    "integration_points": story.get("implementation_notes", {}).get("integration_points", ""),
                    "accessibility": story.get("implementation_notes", {}).get("accessibility", "")
                }
            }

            return validated

        except Exception as e:
            logger.error(f"Error validating user story: {str(e)}")
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
    def _create_error_story(cls, error_msg: str) -> Dict[str, Any]:
        """Create an error story with minimal required fields and proper structure"""
        return {
            "type": "User Story",
            "title": "Error parsing user story",
            "description": {
                "role": "System",
                "goal": "parse the user story correctly",
                "benefit": "properly process the story",
                "formatted": f"As a System, I want to parse the user story correctly, so that I can properly process the story. Error: {error_msg}"
            },
            "technical_domain": "Unknown",
            "complexity": "Medium",
            "business_value": "Medium",
            "story_points": 3,
            "required_skills": [],
            "suggested_assignee": "Unassigned",
            "dependencies": [],
            "acceptance_criteria": [],
            "implementation_notes": {
                "technical_considerations": "Error parsing story",
                "integration_points": "",
                "accessibility": ""
            }
        }
