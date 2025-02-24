import json
import re
from typing import Any, Dict, List, Union

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
            # First try to parse as-is
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            logger.debug("Initial JSON parse failed, attempting repairs")

            # First, check if this is a Markdown code block
            code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str)
            if code_block_match:
                logger.debug("Found markdown code block, extracting content")
                extracted_content = code_block_match.group(1).strip()
                try:
                    # Try to parse the extracted content
                    json.loads(extracted_content)
                    logger.debug("Successfully parsed JSON from markdown code block")
                    return extracted_content
                except json.JSONDecodeError:
                    logger.debug("Extracted content still not valid JSON, continuing with repairs")
                    json_str = extracted_content  # Continue with the extracted content

            logger.debug("Input content:")
            logger.debug("-" * 80)
            logger.debug(json_str)
            logger.debug("-" * 80)

            # First, try to extract JSON from the response
            json_str = JSONSanitizer._extract_json_content(json_str)
            if not json_str:
                logger.error("No JSON-like content found in the response")
                raise ValueError("No JSON-like content found in the response")

            # Store original for logging
            original = json_str

            # Fix common LLM formatting issues
            json_str = JSONSanitizer._fix_common_issues(json_str)

            try:
                # Verify the sanitized string is valid JSON
                json.loads(json_str)
                if json_str != original:
                    logger.info("Successfully repaired JSON")
                    logger.debug("Original content:")
                    logger.debug("-" * 80)
                    logger.debug(original)
                    logger.debug("-" * 80)
                    logger.debug("Repaired content:")
                    logger.debug("-" * 80)
                    logger.debug(json_str)
                    logger.debug("-" * 80)
                return json_str
            except json.JSONDecodeError as e:
                logger.error(f"Failed to repair JSON: {str(e)}")
                logger.error("Error location details:")
                logger.error(f"Line number: {e.lineno}")
                logger.error(f"Column number: {e.colno}")
                logger.error(f"Error position (char): {e.pos}")
                logger.error("Problematic content around error position:")
                # Get context around the error position
                start = max(0, e.pos - 50)
                end = min(len(json_str), e.pos + 50)
                logger.error("-" * 80)
                logger.error(f"...{json_str[start:e.pos]}>>>ERROR HERE<<< {json_str[e.pos:end]}...")
                logger.error("-" * 80)
                logger.error("Full content after attempted repair:")
                logger.error("-" * 80)
                logger.error(json_str)
                logger.error("-" * 80)
                raise

    @staticmethod
    def _fix_common_issues(json_str: str) -> str:
        """Fix common JSON formatting issues from LLM responses"""
        original = json_str
        changes_made = []

        # Fix unescaped quotes in property values
        new_str = re.sub(r':\s*"([^"]*?)(?<!\\)"([^"]*?)"', r': "\1\\\"\2"', json_str)
        if new_str != json_str:
            changes_made.append("Fixed unescaped quotes in property values")
            json_str = new_str

        # Fix unescaped quotes in string arrays
        new_str = re.sub(r'\[\s*"([^"]*?)(?<!\\)"([^"]*?)"\s*\]', r'["\1\\\"\2"]', json_str)
        if new_str != json_str:
            changes_made.append("Fixed unescaped quotes in string arrays")
            json_str = new_str

        # Ensure property names are properly quoted
        new_str = re.sub(r'(\w+)(?=\s*:)', r'"\1"', json_str)
        if new_str != json_str:
            changes_made.append("Added quotes to property names")
            json_str = new_str

        # Fix trailing commas in objects and arrays
        new_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        if new_str != json_str:
            changes_made.append("Removed trailing commas")
            json_str = new_str

        # Fix missing quotes around property values
        new_str = re.sub(r':\s*([^"{}\[\]\s,]+)([,}])', r': "\1"\2', json_str)
        if new_str != json_str:
            changes_made.append("Added quotes around property values")
            json_str = new_str

        # Fix newlines in string values
        new_str = re.sub(r'"\s*\n\s*([^"]+)\s*\n\s*"', lambda m: f'"{m.group(1)}"', json_str)
        if new_str != json_str:
            changes_made.append("Fixed newlines in string values")
            json_str = new_str

        if changes_made:
            logger.debug("JSON fixes applied:")
            for change in changes_made:
                logger.debug(f"- {change}")

        return json_str

    @staticmethod
    def _extract_json_content(content: str) -> str:
        """Extract JSON content from LLM response"""
        logger.debug("Attempting to extract JSON content")

        # Try to find JSON array or object
        array_match = re.search(r'\[\s*{.*}\s*\]', content, re.DOTALL)
        object_match = re.search(r'{\s*".*}\s*', content, re.DOTALL)

        if array_match:
            logger.debug("Found JSON array structure")
            return array_match.group(0)
        elif object_match:
            logger.debug("Found JSON object structure")
            return object_match.group(0)

        # If no clear JSON structure found, try to find content between code blocks
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if code_block_match:
            logger.debug("Found JSON content in code block")
            return code_block_match.group(1)

        logger.debug("No structured JSON content found, returning original content")
        return content

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
            # First try direct parsing
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.debug(f"Initial parse failed: {str(e)}")
                logger.debug("Attempting repair...")

            # Try extracting and sanitizing
            sanitized = JSONSanitizer.sanitize_json_string(json_str)
            return json.loads(sanitized)

        except Exception as e:
            logger.error(f"Failed to parse JSON even after repairs: {str(e)}")
            logger.error("Original content:")
            logger.error("-" * 80)
            logger.error(json_str)
            logger.error("-" * 80)
            return fallback
