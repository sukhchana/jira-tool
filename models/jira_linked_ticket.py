from pydantic import BaseModel, Field


class JiraLinkedTicket(BaseModel):
    """Model representing a linked JIRA ticket"""
    key: str = Field(..., description="The JIRA ticket key (e.g. PROJ-123)")
    summary: str = Field(..., description="The ticket's summary/title")
    relationship: str = Field(None, description="Relationship to the main ticket (e.g., 'blocks', 'relates to')")
    link_type: str = Field("relates to", description="Type of link (e.g., 'blocks', 'is blocked by', 'relates to')")
    status: str = Field("To Do", description="Current status of the ticket")
    issue_type: str = Field("Task", description="The type of issue (Epic, Story, Task, etc.)") 