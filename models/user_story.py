from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from .code_block import CodeBlock
from .gherkin import GherkinScenario
from .implementation_notes import ImplementationNotes
from .research_summary import ResearchSummary
from .story_description import StoryDescription


class UserStory(BaseModel):
    """Complete user story model"""
    id: Optional[str] = Field(None, description="The ID of the user story")
    title: str = Field(..., description="The title of the user story")
    type: str = Field("User Story", description="The type of the story")
    description: StoryDescription = Field(..., description="The structured description of the user story")
    technical_domain: str = Field(..., description="The technical domain this story belongs to")
    complexity: str = Field("Medium", description="The complexity level (Low, Medium, High)")
    business_value: str = Field("Medium", description="The business value level (Low, Medium, High)")
    story_points: int = Field(3, description="Story points (1, 2, 3, 5, 8, 13)")
    required_skills: List[str] = Field(default_factory=list, description="List of required technical skills")
    suggested_assignee: str = Field("Unassigned", description="Role best suited for this story")
    dependencies: List[str] = Field(default_factory=list, description="List of dependent tasks")
    acceptance_criteria: List[str] = Field(default_factory=list, description="List of acceptance criteria")
    implementation_notes: ImplementationNotes = Field(default_factory=ImplementationNotes,
                                                      description="Implementation notes")

    # Additional components generated separately
    research_summary: Optional[ResearchSummary] = Field(None, description="Research summary for the story")
    code_blocks: List[CodeBlock] = Field(default_factory=list, description="Example code blocks")
    scenarios: List[GherkinScenario] = Field(default_factory=list,
                                             description="Acceptance criteria as Gherkin scenarios")

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to ensure type field is always included"""
        data = super().model_dump(**kwargs)
        if "type" not in data:
            data["type"] = "User Story"
        return data
