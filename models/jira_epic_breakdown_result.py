from pydantic import BaseModel, Field
from datetime import datetime
from .epic_info import EpicInfo
from .analysis_info import AnalysisInfo
from .breakdown_info import BreakdownInfo
from .metrics_info import MetricsInfo

class JiraEpicBreakdownResult(BaseModel):
    status: str = "success"
    timestamp: datetime = Field(default_factory=datetime.now)
    epic: EpicInfo
    analysis: AnalysisInfo
    breakdown: BreakdownInfo
    metrics: MetricsInfo 