from pydantic import BaseModel
from typing import Optional, Dict, Any

class JiraTicketDetails(BaseModel):
    """Response model for JIRA ticket details"""
    key: str
    summary: str
    description: Optional[str]
    status: str
    created: str
    updated: str
    fields: Dict[str, Any]  # For any additional JIRA fields 