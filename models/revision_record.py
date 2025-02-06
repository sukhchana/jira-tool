from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class RevisionRecord(BaseModel):
    """Model for storing revision records"""
    revision_id: str = Field(..., description="UUID of the revision")
    execution_id: str = Field(..., description="UUID of the execution being revised")
    ticket_id: str = Field(..., description="ID of the ticket being revised")
    proposed_plan_file: str = Field(..., description="Path to the proposed plan file")
    execution_plan_file: str = Field(..., description="Path to the execution plan file")
    status: str = Field(..., description="Status of the revision (PENDING/ACCEPTED/REJECTED)")
    created_at: datetime = Field(..., description="When the revision was created")
    changes_requested: str = Field(..., description="Original change request")
    changes_interpreted: str = Field(..., description="Interpreted changes by LLM")
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None

class RevisionConfirmation(BaseModel):
    """Model for confirming a revision request"""
    original_execution_id: str = Field(..., description="UUID of the original execution")
    ticket_id: str = Field(..., description="ID of the ticket being revised")
    interpreted_changes: str = Field(..., description="LLM's interpretation of the changes")
    temp_revision_id: str = Field(..., description="Temporary ID for this revision")
    confirmation_required: bool = Field(default=True, description="Whether confirmation is required")
    status: Optional[str] = Field(None, description="Status of the revision (ACCEPTED/REJECTED)") 