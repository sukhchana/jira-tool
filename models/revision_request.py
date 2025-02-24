from pydantic import BaseModel, Field


class RevisionRequest(BaseModel):
    """Model for requesting a revision to a ticket"""
    revision_request: str = Field(..., description="Description of the requested changes to the ticket")

    class Config:
        json_schema_extra = {
            "example": {
                "revision_request": "Please add error handling to the acceptance criteria"
            }
        }


class RevisionConfirmation(BaseModel):
    """Response model for confirming revision interpretation"""
    original_execution_id: str
    interpreted_changes: str
    temp_revision_id: str
    confirmation_required: bool = True
    status: str = "PENDING"


class RevisionResponse(BaseModel):
    """Response model for confirmed revision"""
    original_execution_id: str
    new_execution_id: str
    changes_made: str
    new_plan_file: str
