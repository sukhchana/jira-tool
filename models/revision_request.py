from pydantic import BaseModel, Field

class RevisionRequest(BaseModel):
    """Request model for proposing changes to an execution plan"""
    execution_id: str = Field(..., description="UUID of the execution to revise")
    revision_request: str = Field(..., min_length=1, description="Description of the requested changes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "01HMW123ABC...",
                "revision_request": "Please add a new task for unit testing"
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