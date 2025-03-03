from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class SubTask(BaseModel):
    """Model representing a JIRA subtask"""
    id: Optional[str] = Field(None, description="The ID of the subtask")
    title: str = Field(..., description="Clear, descriptive title of the subtask")
    type: str = Field("Sub-task", description="The type of the task")
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

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to ensure type field is always included"""
        data = super().model_dump(**kwargs)
        if "type" not in data:
            data["type"] = "Sub-task"
        return data
