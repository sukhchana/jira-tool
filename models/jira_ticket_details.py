from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class JiraTicketDetails(BaseModel):
    """Model representing a JIRA ticket's details"""
    key: str = Field(..., description="The JIRA ticket key (e.g. PROJ-123)")
    summary: str = Field(..., description="The ticket's summary/title")
    description: str = Field("", description="The ticket's detailed description")
    issue_type: str = Field(..., description="The type of issue (Epic, Story, Task, etc.)")
    status: str = Field(..., description="Current status of the ticket")
    project_key: str = Field(..., description="The key of the project this ticket belongs to")
    created: str = Field(..., description="Timestamp when the ticket was created")
    updated: str = Field(..., description="Timestamp when the ticket was last updated")
    assignee: Optional[str] = Field(None, description="Username of the assigned user")
    reporter: Optional[str] = Field(None, description="Username of the reporter")
    priority: Optional[str] = Field(None, description="Priority level of the ticket")
    labels: List[str] = Field(default_factory=list, description="List of labels attached to the ticket")
    components: List[str] = Field(default_factory=list, description="List of components this ticket belongs to")
    parent_key: Optional[str] = Field(None, description="Key of the parent ticket (if any)")
    epic_key: Optional[str] = Field(None, description="Key of the epic this ticket belongs to (if any)")
    story_points: Optional[int] = Field(None, description="Story points estimate")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Any additional custom fields")
