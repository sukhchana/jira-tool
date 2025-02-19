from typing import Any, Dict, List, Union
import json
import re
from loguru import logger

class JSONSanitizer:
    """Utility class to sanitize and repair malformed JSON from LLM responses"""
    
    @staticmethod
    def sanitize_json_string(json_str: str) -> str:
        """
        Sanitize a JSON string by fixing common LLM JSON formatting issues.
        
        Args:
            json_str: The potentially malformed JSON string
            
        Returns:
            A sanitized JSON string that should be parseable
        """
        try:
            # If it's already valid JSON, return as is
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            logger.debug(f"Initial JSON parse failed: {str(e)}, attempting repairs")
            
            # Store original for logging
            original = json_str
            
            # Fix unescaped quotes in property values
            json_str = re.sub(r':\s*"([^"]*?)(?<!\\)"([^"]*?)"', r': "\1\\\"\2"', json_str)
            
            # Fix unescaped quotes in string arrays
            json_str = re.sub(r'\[\s*"([^"]*?)(?<!\\)"([^"]*?)"\s*\]', r'["\1\\\"\2"]', json_str)
            
            # Ensure property names are properly quoted
            json_str = re.sub(r'(\w+)(?=\s*:)', r'"\1"', json_str)
            
            # Fix trailing commas in objects and arrays
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix missing quotes around property values
            json_str = re.sub(r':\s*([^"{}\[\]\s,]+)([,}])', r': "\1"\2', json_str)
            
            try:
                # Verify the sanitized string is valid JSON
                json.loads(json_str)
                if json_str != original:
                    logger.info("Successfully repaired JSON")
                    logger.debug(f"Original: {original}")
                    logger.debug(f"Repaired: {json_str}")
                return json_str
            except json.JSONDecodeError as e:
                logger.error(f"Failed to repair JSON: {str(e)}")
                logger.debug(f"Attempted repair result: {json_str}")
                raise
    
    @staticmethod
    def safe_parse(json_str: str) -> Union[Dict[str, Any], List[Any]]:
        """
        Safely parse a JSON string, attempting repairs if needed.
        
        Args:
            json_str: The JSON string to parse
            
        Returns:
            The parsed JSON data
            
        Raises:
            json.JSONDecodeError if the JSON cannot be parsed even after repairs
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            sanitized = JSONSanitizer.sanitize_json_string(json_str)
            return json.loads(sanitized)
    
    @staticmethod
    def safe_parse_with_fallback(
        json_str: str,
        fallback: Union[Dict[str, Any], List[Any], None] = None
    ) -> Union[Dict[str, Any], List[Any], None]:
        """
        Safely parse JSON with a fallback value if parsing fails.
        
        Args:
            json_str: The JSON string to parse
            fallback: Value to return if parsing fails (default: None)
            
        Returns:
            The parsed JSON data or the fallback value
        """
        try:
            return JSONSanitizer.safe_parse(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON even after repairs: {str(e)}")
            return fallback 