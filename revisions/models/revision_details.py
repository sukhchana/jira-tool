from datetime import datetime
from typing import Optional

from pydantic import Field

from models.base_model import BaseModel


class RevisionDetails(BaseModel):
    """Model for storing revision information"""
    revision_id: str = Field(..., description="UUID of the revision")
    execution_id: str = Field(..., description="UUID of the execution being revised")
    ticket_id: str = Field(..., description="ID of the ticket being revised")
    epic_key: str = Field(..., description="The JIRA epic key this revision belongs to")
    interpreted_changes: str = Field(..., description="LLM's interpretation of the changes")
    changes_requested: str = Field(..., description="Original change request")
    proposed_plan_file: str = Field(..., description="Path to the proposed plan file")
    execution_plan_file: str = Field(..., description="Path to the execution plan file")
    status: str = Field(..., description="Status of the revision")
    created_at: datetime = Field(..., description="When the revision was created")
    updated_at: Optional[datetime] = Field(None, description="When the revision was last updated")
    accepted: Optional[bool] = Field(None, description="Whether the revision was accepted")
    accepted_at: Optional[datetime] = Field(None, description="When the revision was accepted")
