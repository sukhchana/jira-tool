from pydantic import BaseModel

class JiraTaskDefinition(BaseModel):
    """Represents a high-level JIRA task definition"""
    id: str
    type: str
    name: str
    complexity: str 