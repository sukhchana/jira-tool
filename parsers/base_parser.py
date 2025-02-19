from typing import Dict, Any, List, Optional, Union
from loguru import logger
import re
import json
from utils.json_sanitizer import JSONSanitizer

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

    @staticmethod
    def parse_json_content(content: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
        """
        Parse JSON content from LLM response, attempting repairs if needed.
        
        Args:
            content: The content string potentially containing JSON
            
        Returns:
            Parsed JSON data or None if parsing fails
        """
        try:
            # Try to find JSON content within the string
            # Look for common patterns like ```json or just { or [
            json_start = content.find('{')
            array_start = content.find('[')
            
            if json_start == -1 and array_start == -1:
                logger.warning("No JSON-like content found in string")
                return None
            
            # Use the earlier of the two starts if both exist
            if json_start == -1:
                start_pos = array_start
            elif array_start == -1:
                start_pos = json_start
            else:
                start_pos = min(json_start, array_start)
            
            # Find the matching end
            end_char = '}' if content[start_pos] == '{' else ']'
            end_pos = content.rfind(end_char)
            
            if end_pos == -1:
                logger.error(f"No matching {end_char} found for JSON content")
                return None
            
            # Extract the JSON content
            json_content = content[start_pos:end_pos + 1]
            
            # Remove any markdown code block markers
            json_content = json_content.replace('```json', '').replace('```', '').strip()
            
            logger.debug(f"Attempting to parse JSON content: {json_content}")
            
            # Use the sanitizer to parse the content
            return JSONSanitizer.safe_parse_with_fallback(json_content)
            
        except Exception as e:
            logger.error(f"Failed to parse JSON content: {str(e)}")
            logger.debug(f"Original content: {content}")
            return None
    
    @staticmethod
    def extract_code_blocks(content: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from markdown-formatted content.
        
        Args:
            content: The markdown content string
            
        Returns:
            List of dictionaries containing language and code
        """
        try:
            # Find all code blocks with or without language specifiers
            code_blocks = []
            lines = content.split('\n')
            current_block = None
            
            for line in lines:
                if line.startswith('```'):
                    if current_block is None:
                        # Start of a new code block
                        lang = line[3:].strip()
                        current_block = {
                            'language': lang if lang else 'text',
                            'code': []
                        }
                    else:
                        # End of current code block
                        current_block['code'] = '\n'.join(current_block['code'])
                        code_blocks.append(current_block)
                        current_block = None
                elif current_block is not None:
                    current_block['code'].append(line)
            
            return code_blocks
            
        except Exception as e:
            logger.error(f"Failed to extract code blocks: {str(e)}")
            return [] 