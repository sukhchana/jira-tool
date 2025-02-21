from typing import Dict, Any, List
from loguru import logger
import json
from .base_parser import BaseParser
from utils.config import settings

class CodeBlockParser(BaseParser):
    """Parser for code block content"""
    
    @classmethod
    def parse(cls, content: str) -> List[Dict[str, Any]]:
        """Parse code blocks from content"""
        # If code block generation is disabled, return empty list
        if not settings.ENABLE_CODE_BLOCK_GENERATION:
            return []
            
        try:
            # Parse JSON array, handling markdown code blocks
            code_blocks = cls.parse_json_content(content)
            if not isinstance(code_blocks, list):
                logger.error("Response is not a JSON array")
                return cls._create_fallback_block(content)
            
            # Validate and clean each code block
            validated_blocks = []
            for block in code_blocks:
                if cls._validate_code_block(block):
                    validated_blocks.append({
                        "language": block["language"].lower(),
                        "description": cls._clean_text(block["description"]),
                        "code": cls._clean_text(block["code"])
                    })
            
            return validated_blocks if validated_blocks else cls._create_fallback_block(content)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response:\n{content}")
            return cls._create_fallback_block(content)
        except Exception as e:
            logger.error(f"Failed to parse code blocks: {str(e)}")
            logger.error(f"Content that caused error:\n{content}")
            return cls._create_fallback_block(content)
    
    @staticmethod
    def _validate_code_block(block: Dict[str, Any]) -> bool:
        """Validate a code block has all required fields"""
        required_fields = ["language", "description", "code"]
        return all(field in block and block[field] for field in required_fields)
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean text by removing extra whitespace"""
        if not text:
            return text
        return text.strip()
    
    @staticmethod
    def _create_error_block() -> List[Dict[str, Any]]:
        """Create an error code block"""
        return [{
            "language": "text",
            "description": "Error parsing code blocks",
            "code": "Error parsing code blocks"
        }]

    @staticmethod
    def _create_fallback_block(content: str) -> List[Dict[str, Any]]:
        """Create a fallback code block containing the entire response"""
        return [{
            "language": "text",
            "description": "Raw LLM response (parsing failed)",
            "code": content.strip()
        }] 