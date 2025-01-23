from pydantic import BaseModel
from typing import Optional, Dict, Any

class TicketGenerationRequest(BaseModel):
    """Request model for generating a JIRA ticket description"""
    context: str
    requirements: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None 