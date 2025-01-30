from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime
from .epic_info import EpicInfo
from .analysis_info import AnalysisInfo
from .breakdown_info import BreakdownInfo
from .metrics_info import MetricsInfo

class JiraEpicBreakdownResult(BaseModel):
    execution_id: str = Field(..., description="UUID7 of the execution")
    epic_key: str
    epic_summary: str
    analysis: Dict[str, Any]
    tasks: List[Dict[str, Any]]
    execution_plan_file: str
    proposed_tickets_file: str
    status: str = "success"
    timestamp: datetime = Field(default_factory=datetime.now)
    epic: EpicInfo
    breakdown: BreakdownInfo
    metrics: MetricsInfo 