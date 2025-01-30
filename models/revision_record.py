from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class RevisionRecord(BaseModel):
    revision_id: str = Field(..., description="UUID7 of the revision")
    execution_id: str = Field(..., description="UUID7 of the parent execution")
    proposed_plan_file: str
    execution_plan_file: str
    status: str
    created_at: datetime
    changes_requested: str
    changes_interpreted: str
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None 