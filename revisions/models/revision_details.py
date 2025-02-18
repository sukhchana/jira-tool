from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class RevisionDetails:
    """Data class for storing revision information"""
    revision_id: str
    execution_id: str
    ticket_id: str
    epic_key: str
    interpreted_changes: str
    changes_requested: str
    proposed_plan_file: str
    execution_plan_file: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None 