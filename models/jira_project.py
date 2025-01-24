from pydantic import BaseModel

class JiraProject(BaseModel):
    """Response model for JIRA project details"""
    key: str
    name: str
    id: str 