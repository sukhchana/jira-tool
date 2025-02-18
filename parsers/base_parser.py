from typing import Dict, Any, List, Optional
from loguru import logger
import re
import json

class BaseParser:
    """Base class for all parsers with common functionality"""
    
    @staticmethod
    def _validate_enum(value: str, valid_values: List[str], default: str) -> str:
        """Validate that a value is in a list of valid values, return default if not"""
        cleaned_value = value.strip().title()
        return cleaned_value if cleaned_value in valid_values else default
    
    @staticmethod
    def extract_section(content: str, section_name: str, end_pattern: str = None) -> Optional[str]:
        """Extract a section from content using regex"""
        try:
            # Use raw string for the pattern and handle the end pattern separately
            base_pattern = fr"{section_name}:\s*(.+?)"
            end = fr"(?={end_pattern})" if end_pattern else r"(?=\n|$)"
            pattern = base_pattern + end
            
            match = re.search(pattern, content, re.DOTALL)
            return match.group(1).strip() if match else None
        except Exception as e:
            logger.error(f"Error extracting section {section_name}: {str(e)}")
            return None
    
    @staticmethod
    def extract_list_items(content: str) -> List[str]:
        """Extract list items from content, handling various formats"""
        items = []
        if not content:
            return items
            
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith(("- ", "* ", "• ")):
                items.append(line[2:].strip())
            elif line[0].isdigit() and ". " in line:
                items.append(line.split(". ", 1)[1].strip())
            elif line:
                items.append(line)
        return items
    
    @staticmethod
    def extract_between_tags(content: str, tag_name: str) -> Optional[str]:
        """Extract content between XML-style tags"""
        try:
            pattern = fr"<{tag_name}>(.*?)</{tag_name}>"
            match = re.search(pattern, content, re.DOTALL)
            return match.group(1) if match else None
        except Exception as e:
            logger.error(f"Error extracting content between {tag_name} tags: {str(e)}")
            return None
    
    @staticmethod
    def extract_key_value(line: str, key: str) -> Optional[str]:
        """Extract value from a key:value line"""
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
        return None

    @staticmethod
    def extract_json_from_markdown(content: str) -> str:
        """Extract JSON content from markdown code blocks if present"""
        try:
            # Try to find JSON in code block
            code_block_pattern = r"```(?:json)?\n([\s\S]*?)\n```"
            match = re.search(code_block_pattern, content)
            
            if match:
                # Found JSON in code block, extract and clean it
                json_content = match.group(1).strip()
                logger.debug("Extracted JSON from code block")
                return json_content
            
            # If no code block found, return original content
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error extracting JSON from markdown: {str(e)}")
            return content.strip()

    @classmethod
    def parse_json_content(cls, content: str) -> Any:
        """Parse JSON content, handling markdown code blocks"""
        try:
            # First try parsing directly
            return json.loads(content)
        except json.JSONDecodeError:
            # If direct parsing fails, try extracting from markdown
            cleaned_content = cls.extract_json_from_markdown(content)
            try:
                return json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON after extraction: {str(e)}")
                raise 