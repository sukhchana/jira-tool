from pydantic import BaseModel, Field
from typing import List

class SubTask(BaseModel):
    """Model representing a JIRA subtask"""
    title: str = Field(..., description="Clear, descriptive title of the subtask")
    description: str = Field(..., description="Detailed description of what needs to be implemented")
    technical_domain: str = Field(..., description="Primary technical domain this subtask belongs to")
    complexity: str = Field(..., description="Low|Medium|High")
    business_value: str = Field(..., description="Low|Medium|High")
    story_points: int = Field(..., description="1|2|3|5|8|13")
    required_skills: List[str] = Field(default_factory=list, description="List of required technical skills")
    suggested_assignee: str = Field(..., description="Role best suited for this task")
    dependencies: List[str] = Field(default_factory=list, description="List of dependencies")
    acceptance_criteria: List[str] = Field(..., description="List of acceptance criteria")
    parent_id: str = Field(..., description="ID of the parent task") 