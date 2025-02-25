from datetime import datetime, UTC
from typing import List, Dict, Any, Optional

from pydantic import Field

from .analysis_info import AnalysisInfo
from .base_model import BaseModel
from .breakdown_info import BreakdownInfo
from .metrics_info import MetricsInfo
from .task_group import TaskGroup


class EpicBreakdownResponse(BaseModel):
    """Response model containing the complete epic breakdown
    
    This model represents the unified response for epic breakdown operations,
    whether they are being stored in the database or returned via API.
    """
    # Execution metadata
    execution_id: str = Field(..., description="UUID7 of the execution")
    status: str = "success"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Epic information
    epic_key: str
    epic_summary: str

    # Analysis and breakdown
    analysis: AnalysisInfo
    breakdown: BreakdownInfo
    metrics: MetricsInfo
    tasks: List[TaskGroup]

    # File references
    execution_plan_file: Optional[str] = None
    proposed_tickets_file: Optional[str] = None

    # JIRA integration results
    created_jira_tasks: Optional[List[Dict[str, Any]]] = None
