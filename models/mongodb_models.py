from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid_extensions import uuid7

class ExecutionModel(BaseModel):
    """Model for execution records"""
    execution_id: str = Field(default_factory=lambda: str(uuid7()))
    epic_key: str
    execution_plan_file: str
    proposed_plan_file: str
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "NEW"
    parent_execution_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RevisionModel(BaseModel):
    """Model for revision records"""
    revision_id: str = Field(default_factory=lambda: str(uuid7()))
    execution_id: str
    proposed_plan_file: str
    execution_plan_file: str
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=datetime.now)
    changes_requested: str
    changes_interpreted: str
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TaskModel(BaseModel):
    """Model for task details"""
    task_id: str
    task_type: str
    name: str
    description: str
    technical_domain: str
    complexity: str
    dependencies: List[str]
    business_value: Optional[str] = None
    implementation_notes: Optional[str] = None

class SubtaskModel(BaseModel):
    """Model for subtask details"""
    subtask_id: str
    title: str
    description: str
    acceptance_criteria: str
    required_skills: List[str]
    story_points: int
    suggested_assignee: str

class ProposedTicketModel(BaseModel):
    """Model for proposed tickets"""
    proposal_id: str
    execution_id: str
    epic_key: str
    task_id: str
    task_type: str
    parent_task_id: Optional[str] = None
    task_details: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ProposalCounterModel(BaseModel):
    """Model for proposal counters"""
    proposal_id: str
    counter_data: Dict[str, int]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 