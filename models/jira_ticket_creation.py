from pydantic import BaseModel, Field
from datetime import datetime


class JiraTicketCreation(BaseModel):
    """Model representing the response from creating a JIRA ticket"""
    key: str = Field(..., description="The JIRA ticket key (e.g. PROJ-123)")
    summary: str = Field(..., description="The ticket's summary/title")
    status: str = Field("To Do", description="Initial status of the created ticket")
    issue_type: str = Field("Task", description="The type of issue created (Epic, Story, Task, etc.)")
    created_date: datetime = Field(default_factory=datetime.now, description="The date and time when the ticket was created") 