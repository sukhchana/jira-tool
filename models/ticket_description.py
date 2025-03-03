from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from .gherkin import GherkinScenario


class TicketDescription(BaseModel):
    """Model for a complete ticket description"""
    title: str = Field("", description="The title of the ticket")
    description: str = Field("", description="The main description of the ticket")
    technical_domain: str = Field("", description="The technical domain this ticket belongs to")
    required_skills: List[str] = Field(default_factory=list, description="List of required skills")
    story_points: int = Field(0, description="Story points estimate")
    suggested_assignee: str = Field("", description="Suggested assignee or role")
    complexity: str = Field("", description="Complexity level")
    acceptance_criteria: List[str] = Field(default_factory=list, description="List of acceptance criteria")
    scenarios: List[GherkinScenario] = Field(default_factory=list, description="List of Gherkin scenarios")
    technical_notes: str = Field("", description="Additional technical notes") 