from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class GherkinStep(BaseModel):
    """A single step in a Gherkin scenario"""
    keyword: str = Field(..., description="The step keyword (Given, When, Then, And)")
    text: str = Field(..., description="The step text")


class GherkinScenario(BaseModel):
    """A Gherkin scenario for a user story"""
    name: str = Field(..., description="The name of the scenario")
    steps: List[GherkinStep] = Field(default_factory=list, description="The steps in the scenario")


class ResearchSummary(BaseModel):
    """Research summary for a user story"""
    pain_points: str = Field(..., description="Current pain points this story addresses")
    success_metrics: str = Field(..., description="Metrics to measure success")
    similar_implementations: str = Field(..., description="Similar implementations or references")
    modern_approaches: str = Field(..., description="Modern approaches and best practices to consider")


class CodeBlock(BaseModel):
    """A code block with its language"""
    language: str = Field(..., description="The programming language of the code")
    description: str = Field(..., description="Description of what the code demonstrates")
    code: str = Field(..., description="The actual code")


class StoryDescription(BaseModel):
    """Structured user story description"""
    role: str = Field(..., description="The user role/persona")
    goal: str = Field(..., description="What the user wants to accomplish")
    benefit: str = Field(..., description="The value/benefit to the user")
    formatted: str = Field(..., description="Formatted as: As a [role], I want [goal], so that [benefit]")


class ImplementationNotes(BaseModel):
    """Implementation notes for a user story"""
    technical_considerations: str = Field("", description="Key technical aspects to consider")
    integration_points: str = Field("", description="Integration requirements")
    accessibility: str = Field("", description="Accessibility requirements")


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
