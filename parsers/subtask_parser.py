from typing import Dict, Any, Optional, List
from loguru import logger
from .base_parser import BaseParser
from models.sub_task import SubTask
import re
import xml.etree.ElementTree as ET

class SubtaskParser(BaseParser):
    """Parser for subtasks"""
    
    @classmethod
    def parse(cls, content: str) -> List[SubTask]:
        """
        Parse subtasks from content.
        
        Args:
            content: The content string containing one or more subtasks
            
        Returns:
            List of SubTask objects
        """
        try:
            # Clean up the content first
            content = cls._clean_xml_content(content)
            logger.debug(f"Parsing subtask content of length: {len(content)}")
            
            # Split content into individual subtasks if multiple exist
            subtask_contents = cls._split_into_subtasks(content)
            subtasks = []
            
            for subtask_content in subtask_contents:
                try:
                    # Ensure proper XML structure
                    if not subtask_content.strip().startswith("<subtask>"):
                        subtask_content = f"<subtask>{subtask_content}</subtask>"

                    # Extract fields using regex patterns
                    subtask = SubTask(
                        title=cls._extract_xml_content(subtask_content, "title", "Untitled Subtask"),
                        description=cls._extract_xml_content(subtask_content, "description", "No description provided"),
                        story_points=cls._parse_story_points(cls._extract_xml_content(subtask_content, "story_points", "3")),
                        required_skills=cls._parse_list_items_from_text(
                            cls._extract_xml_content(subtask_content, "technical_details/required_skills", "")
                        ),
                        suggested_assignee=cls._extract_xml_content(subtask_content, "technical_details/suggested_assignee", "Unassigned"),
                        dependencies=cls._extract_xml_list(subtask_content, "dependencies/dependency"),
                        acceptance_criteria=cls._extract_xml_content(subtask_content, "acceptance_criteria", "")
                    )
                    subtasks.append(subtask)
                        
                except Exception as e:
                    logger.error(f"Failed to parse individual subtask: {str(e)}")
                    logger.error(f"Subtask content:\n{subtask_content}")
                    subtasks.append(cls._create_error_subtask(str(e)))
            
            return subtasks if subtasks else [cls._create_error_subtask("No valid subtasks found")]
            
        except Exception as e:
            logger.error(f"Failed to parse subtasks: {str(e)}")
            logger.error(f"Content:\n{content}")
            return [cls._create_error_subtask(str(e))]

    @classmethod
    def _extract_xml_content(cls, content: str, path: str, default: str = "") -> str:
        """Extract content from XML-like structure using regex"""
        # Convert path to regex pattern
        pattern = path.replace('/', '/.*?')
        regex = f"<{pattern}>(.*?)</{pattern.split('/')[-1]}>"
        match = re.search(regex, content, re.DOTALL | re.IGNORECASE)
        return cls._clean_text(match.group(1)) if match else default

    @classmethod
    def _extract_xml_list(cls, content: str, path: str) -> List[str]:
        """Extract list of items from XML-like structure"""
        pattern = path.replace('/', '/.*?')
        regex = f"<{pattern}>(.*?)</{pattern.split('/')[-1]}>"
        matches = re.finditer(regex, content, re.DOTALL | re.IGNORECASE)
        return [cls._clean_text(m.group(1)) for m in matches if m.group(1).strip()]

    @classmethod
    def _extract_code_blocks(cls, content: str) -> List[Dict[str, str]]:
        """Extract code blocks with their language"""
        blocks = []
        pattern = r'<code\s+language=["\']([^"\']*)["\']>(.*?)</code>'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            language = match.group(1) or "text"
            code = cls._clean_text(match.group(2))
            if code:
                blocks.append({
                    "language": language,
                    "code": code
                })
        return blocks

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Clean text by removing markdown and extra whitespace"""
        if not text:
            return text
        # Remove markdown formatting
        text = re.sub(r'\*\*|__|`', '', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.strip()

    @classmethod
    def _parse_story_points(cls, points_text: str) -> int:
        """Parse and validate story points"""
        try:
            points = int(re.search(r'\d+', points_text).group())
            valid_points = [1, 2, 3, 5, 8, 13]
            return min(valid_points, key=lambda x: abs(x - points))
        except (ValueError, AttributeError):
            return 3

    @classmethod
    def _create_error_subtask(cls, error_msg: str) -> SubTask:
        """Create an error subtask with minimal required fields"""
        return SubTask(
            title="Error parsing subtask",
            description=f"Failed to parse: {error_msg}",
            story_points=3,
            required_skills=[],
            suggested_assignee="Unassigned",
            dependencies=[],
            acceptance_criteria="Error occurred during parsing"
        )

    @classmethod
    def _clean_xml_content(cls, content: str) -> str:
        """Clean up XML content for parsing"""
        # Normalize newlines
        content = content.replace('\r\n', '\n')
        # Preserve newlines in code blocks
        code_blocks = re.finditer(r'(<code[^>]*>)(.*?)(</code>)', content, re.DOTALL)
        for block in code_blocks:
            preserved = block.group(2).replace('\n', '{{NEWLINE}}')
            content = content.replace(block.group(0), f'{block.group(1)}{preserved}{block.group(3)}')
        # Clean up general whitespace
        content = re.sub(r'\s+', ' ', content)
        # Restore newlines in code blocks
        content = content.replace('{{NEWLINE}}', '\n')
        return content.strip()

    @classmethod
    def _parse_list_items_from_text(cls, text: str) -> List[str]:
        """Parse a comma/semicolon separated text into a list of items"""
        if not text:
            return []
            
        # Split by common separators and clean up
        items = [
            cls._clean_text(item.strip())
            for item in re.split(r'[,;]|\band\b', text)
            if item.strip() and item.strip().lower() not in ['none', 'n/a', '-']
        ]
        
        return items

    @classmethod
    def _split_into_subtasks(cls, content: str) -> List[str]:
        """Split content into individual subtask blocks"""
        # Try to split by <subtask> tags first
        subtasks = re.findall(r'<subtask>.*?</subtask>', content, re.DOTALL)
        if subtasks:
            return subtasks
            
        # If no <subtask> tags found, try to split by numbered items
        subtasks = re.split(r'\n\s*\d+\.\s+', content)
        if len(subtasks) > 1:
            # Remove empty or whitespace-only items
            return [s.strip() for s in subtasks[1:] if s.strip()]
            
        # If no clear separation found, treat as single subtask
        return [content] if content.strip() else [] 