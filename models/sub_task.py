from pydantic import BaseModel
from typing import List

class SubTask(BaseModel):
    """Model representing a JIRA subtask"""
    title: str
    description: str
    acceptance_criteria: str
    story_points: int
    required_skills: List[str]
    dependencies: List[str]
    suggested_assignee: str 