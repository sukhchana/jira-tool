from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ExecutionRecord(BaseModel):
    execution_id: str = Field(..., description="UUID7 of the execution")
    epic_key: str
    execution_plan_file: str
    proposed_plan_file: str
    status: str
    created_at: datetime
    parent_execution_id: Optional[str] = None 