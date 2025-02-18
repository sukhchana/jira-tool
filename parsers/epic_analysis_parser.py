from typing import Dict, Any, List, Optional
from loguru import logger
import xml.etree.ElementTree as ET
import re
from .base_parser import BaseParser

class EpicAnalysisParser(BaseParser):
    """Parser for epic analysis responses"""
    
    SECTIONS = [
        ("main_objective", "main_objective"),
        ("stakeholders", "stakeholders"),
        ("core_requirements", "core_requirements"),
        ("technical_domains", "technical_domains"),
        ("dependencies", "dependencies"),
        ("challenges", "challenges"),
        ("industry_context", "industry_context")
    ]
    
    @classmethod
    async def parse_with_format_fixing(cls, content: str, format_fixer) -> Dict[str, Any]:
        """Parse epic analysis with format fixing support"""
        try:
            # Try parsing directly first
            result = cls.parse(content)
            if cls._is_valid_epic_analysis(result):
                return result
        except Exception as e:
            logger.warning(f"Initial epic analysis parsing failed: {str(e)}")

        # Try to fix the format
        fixed_result = await format_fixer.fix_format(
            content=content,
            content_type="epic_analysis"
        )
        if fixed_result:
            return fixed_result

        # Return error result if fixing failed
        return {
            "main_objective": "Error parsing epic analysis",
            "stakeholders": [],
            "core_requirements": [],
            "technical_domains": [],
            "dependencies": [],
            "challenges": [],
            "industry_context": []
        }

    @classmethod
    def _is_valid_epic_analysis(cls, result: Dict[str, Any]) -> bool:
        """Check if epic analysis result is valid"""
        if not result:
            return False
            
        required_fields = ["main_objective", "stakeholders", "core_requirements"]
        return all(
            isinstance(result.get(field), (str, list)) and result.get(field)
            for field in required_fields
        )

    @classmethod
    def parse(cls, text: str) -> Dict[str, Any]:
        """Parse the epic analysis response into structured format"""
        try:
            # Extract content between <analysis> tags
            analysis_content = cls.extract_between_tags(text, "analysis")
            if not analysis_content:
                raise ValueError("No content found between <analysis> tags")
            
            sections = {
                "main_objective": "",
                "stakeholders": [],
                "core_requirements": [],
                "technical_domains": [],
                "dependencies": [],
                "challenges": [],
                "industry_context": []
            }
            
            # Process each section using XML tags
            for section_key, tag_name in cls.SECTIONS:
                section_content = cls.extract_between_tags(analysis_content, tag_name)
                if section_content:
                    if section_key == "main_objective":
                        sections[section_key] = section_content.strip()
                    else:
                        # Extract list items, removing empty lines and list markers
                        items = [
                            item.strip().lstrip("- ").lstrip("* ").lstrip("• ")
                            for item in section_content.split("\n")
                            if item.strip() and not item.strip().startswith(("<", ">"))
                        ]
                        sections[section_key] = [item for item in items if item]
            
            # Parse summary section if present
            summary = cls.extract_between_tags(text, "summary")
            if summary:
                sections.update(cls._parse_summary(summary))
            
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing epic analysis: {str(e)}")
            logger.error(f"Text that caused error:\n{text}")
            return {
                "main_objective": "Error parsing epic analysis",
                "stakeholders": [],
                "core_requirements": [],
                "technical_domains": [],
                "dependencies": [],
                "challenges": [],
                "industry_context": []
            }
    
    @classmethod
    def _parse_summary(cls, summary_text: str) -> Dict[str, Any]:
        """Parse the summary section with its own XML tags"""
        summary = {}
        
        # Extract numeric fields
        for field in ["total_technical_domains", "total_core_requirements", 
                     "total_dependencies", "total_challenges"]:
            value = cls.extract_between_tags(summary_text, field)
            if value and value.isdigit():
                summary[field] = int(value)
        
        # Extract research findings
        findings = cls.extract_between_tags(summary_text, "research_findings")
        if findings:
            summary["research_findings"] = findings.strip()
        
        return summary 