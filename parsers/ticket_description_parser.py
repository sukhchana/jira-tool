from typing import Dict, Any, List
from loguru import logger
from .base_parser import BaseParser
import re

class TicketDescriptionParser(BaseParser):
    """Parser for ticket descriptions from LLM responses"""
    
    @classmethod
    def parse(cls, response_text: str) -> Dict[str, Any]:
        """Parse the LLM response for ticket description into structured format"""
        logger.debug("Starting to parse ticket description")
        
        try:
            # Extract the ticket content between tags
            content = cls.extract_between_tags(response_text, "ticket")
            if not content:
                raise ValueError("No ticket content found between <ticket> tags")
            
            # Initialize the structured response
            ticket = {
                "title": "",
                "description": "",
                "technical_domain": "",
                "required_skills": [],
                "story_points": 0,
                "suggested_assignee": "",
                "complexity": "",
                "acceptance_criteria": [],
                "scenarios": [],
                "technical_notes": ""
            }
            
            # Extract basic fields
            ticket["title"] = cls.extract_section(content, "Title") or ""
            ticket["description"] = cls.extract_section(content, "Description", r"\nTechnical Domain:") or ""
            ticket["technical_domain"] = cls.extract_section(content, "Technical Domain") or ""
            
            # Extract skills
            skills_text = cls.extract_section(content, "Required Skills")
            if skills_text:
                ticket["required_skills"] = [s.strip() for s in skills_text.split(",")]
            
            # Extract story points
            points_text = cls.extract_section(content, "Story Points")
            if points_text and points_text.isdigit():
                ticket["story_points"] = int(points_text)
            
            # Extract other fields
            ticket["suggested_assignee"] = cls.extract_section(content, "Suggested Assignee") or ""
            ticket["complexity"] = cls.extract_section(content, "Complexity") or ""
            
            # Extract acceptance criteria
            ac_text = cls.extract_section(content, "Acceptance Criteria", r"\nScenarios:")
            if ac_text:
                ticket["acceptance_criteria"] = cls.extract_list_items(ac_text)
            
            # Extract scenarios
            scenarios_text = cls.extract_section(content, "Scenarios", r"\nTechnical Notes:")
            if scenarios_text:
                ticket["scenarios"] = cls._parse_scenarios(scenarios_text)
            
            # Extract technical notes
            ticket["technical_notes"] = cls.extract_section(content, "Technical Notes", r"\n</ticket>") or ""
            
            logger.debug("Successfully parsed ticket description")
            return ticket
            
        except Exception as e:
            logger.error(f"Error parsing ticket description: {str(e)}")
            logger.error(f"Response text:\n{response_text}")
            raise
    
    @classmethod
    def _parse_scenarios(cls, scenarios_text: str) -> List[Dict[str, Any]]:
        """Parse Gherkin scenarios from text"""
        scenarios = []
        scenario_blocks = re.finditer(r'Scenario:.*?(?=Scenario:|$)', scenarios_text, re.DOTALL)
        
        for block in scenario_blocks:
            scenario = {
                "name": "",
                "steps": []
            }
            
            # Get scenario name
            name_match = re.search(r'Scenario:\s*(.+?)(?=\n|$)', block.group(0))
            if name_match:
                scenario["name"] = name_match.group(1).strip()
            
            # Get steps
            steps = re.findall(r'(Given|When|Then|And)\s+(.+?)(?=\n|$)', block.group(0))
            for keyword, text in steps:
                scenario["steps"].append({
                    "keyword": keyword,
                    "text": text.strip()
                })
            
            scenarios.append(scenario)
        
        return scenarios 