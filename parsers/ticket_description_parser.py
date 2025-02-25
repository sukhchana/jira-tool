import re
from typing import Dict, Any, List

from loguru import logger

from models.ticket_description import TicketDescription
from models.gherkin import GherkinScenario, GherkinStep
from .base_parser import BaseParser


class TicketDescriptionParser(BaseParser):
    """Parser for ticket descriptions from LLM responses"""

    @classmethod
    def parse(cls, response_text: str) -> TicketDescription:
        """Parse the LLM response for ticket description into structured format"""
        logger.debug("Starting to parse ticket description")

        try:
            # Extract the ticket content between tags
            content = cls.extract_between_tags(response_text, "ticket")
            if not content:
                raise ValueError("No ticket content found between <ticket> tags")

            # Extract fields
            title = cls.extract_section(content, "Title") or ""
            description = cls.extract_section(content, "Description", r"\nTechnical Domain:") or ""
            technical_domain = cls.extract_section(content, "Technical Domain") or ""
            
            # Extract skills
            skills_text = cls.extract_section(content, "Required Skills")
            required_skills = [s.strip() for s in skills_text.split(",")] if skills_text else []

            # Extract story points
            points_text = cls.extract_section(content, "Story Points")
            story_points = int(points_text) if points_text and points_text.isdigit() else 0

            # Extract other fields
            suggested_assignee = cls.extract_section(content, "Suggested Assignee") or ""
            complexity = cls.extract_section(content, "Complexity") or ""

            # Extract acceptance criteria
            ac_text = cls.extract_section(content, "Acceptance Criteria", r"\nScenarios:")
            acceptance_criteria = cls.extract_list_items(ac_text) if ac_text else []

            # Extract scenarios
            scenarios_text = cls.extract_section(content, "Scenarios", r"\nTechnical Notes:")
            scenarios = cls._parse_scenarios(scenarios_text) if scenarios_text else []

            # Extract technical notes
            technical_notes = cls.extract_section(content, "Technical Notes", r"\n</ticket>") or ""

            # Create and return TicketDescription model
            ticket = TicketDescription(
                title=title,
                description=description,
                technical_domain=technical_domain,
                required_skills=required_skills,
                story_points=story_points,
                suggested_assignee=suggested_assignee,
                complexity=complexity,
                acceptance_criteria=acceptance_criteria,
                scenarios=scenarios,
                technical_notes=technical_notes
            )

            logger.debug("Successfully parsed ticket description")
            return ticket

        except Exception as e:
            logger.error(f"Error parsing ticket description: {str(e)}")
            logger.error(f"Response text:\n{response_text}")
            raise

    @classmethod
    def _parse_scenarios(cls, scenarios_text: str) -> List[GherkinScenario]:
        """Parse Gherkin scenarios from text"""
        scenarios = []
        scenario_blocks = re.finditer(r'Scenario:.*?(?=Scenario:|$)', scenarios_text, re.DOTALL)

        for block in scenario_blocks:
            # Get scenario name
            name_match = re.search(r'Scenario:\s*(.+?)(?=\n|$)', block.group(0))
            if not name_match:
                continue

            # Get steps
            steps = re.findall(r'(Given|When|Then|And)\s+(.+?)(?=\n|$)', block.group(0))
            gherkin_steps = [
                GherkinStep(keyword=keyword, text=text.strip())
                for keyword, text in steps
            ]

            # Create scenario model
            scenario = GherkinScenario(
                name=name_match.group(1).strip(),
                steps=gherkin_steps
            )
            scenarios.append(scenario)

        return scenarios
