from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from .task_group import TaskGroup
from datetime import datetime
from .epic_info import EpicInfo
from .analysis_info import AnalysisInfo
from .breakdown_info import BreakdownInfo
from .metrics_info import MetricsInfo

class EpicBreakdownResponse(BaseModel):
    """Response model containing the complete epic breakdown"""
    status: str = "success"
    timestamp: datetime = Field(default_factory=datetime.now)
    epic: EpicInfo
    analysis: AnalysisInfo
    breakdown: BreakdownInfo
    metrics: MetricsInfo
    epic_key: str
    epic_summary: str
    tasks: List[TaskGroup]
    created_jira_tasks: Optional[List[Dict[str, Any]]] = None
    execution_plan: Optional[str] = None 