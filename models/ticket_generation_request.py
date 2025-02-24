from typing import Optional, Dict, Any

from pydantic import BaseModel


class TicketGenerationRequest(BaseModel):
    """Request model for generating a JIRA ticket description"""
    context: str
    requirements: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None
