from typing import Optional, List

from pydantic import BaseModel


class TicketCreateRequest(BaseModel):
    """Request model for creating a JIRA ticket"""
    project_key: str
    summary: str
    description: str
    issue_type: str = "Task"
    parent_key: Optional[str] = None
    story_points: Optional[int] = None
    labels: Optional[List[str]] = None
    acceptance_criteria: Optional[str] = None
    technical_domain: Optional[str] = None
    epic_link: Optional[str] = None
    priority: Optional[str] = "Medium"
