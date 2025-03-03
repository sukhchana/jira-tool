from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from .jira_ticket_details import JiraTicketDetails


class JiraEpicDetails(BaseModel):
    """Model representing detailed information about a JIRA epic"""
    key: str = Field(..., description="The JIRA epic key (e.g. PROJ-123)")
    summary: str = Field(..., description="The epic's summary/title")
    description: str = Field("", description="The epic's detailed description")
    status: str = Field(..., description="Current status of the epic")
    project_key: str = Field(..., description="The key of the project this epic belongs to")
    created: str = Field(..., description="Timestamp when the epic was created")
    updated: str = Field(..., description="Timestamp when the epic was last updated")
    assignee: Optional[str] = Field(None, description="Username of the assigned user")
    reporter: Optional[str] = Field(None, description="Username of the reporter")
    priority: Optional[str] = Field(None, description="Priority level of the epic")
    labels: List[str] = Field(default_factory=list, description="List of labels attached to the epic")
    components: List[str] = Field(default_factory=list, description="List of components this epic belongs to")
    
    # Epic-specific fields
    stories: List[JiraTicketDetails] = Field(default_factory=list, description="List of story issues linked to this epic")
    tasks: List[JiraTicketDetails] = Field(default_factory=list, description="List of task issues linked to this epic")
    subtasks: List[JiraTicketDetails] = Field(default_factory=list, description="List of subtask issues linked to this epic")
    total_issues: int = Field(0, description="Total count of all linked issues")
    
    # Any additional custom fields
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Any additional custom fields")

    linked_issues: List[JiraTicketDetails] = Field(default_factory=list, description="List of issues linked to this epic") 