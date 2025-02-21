from typing import List, Dict, Any
from .epic_breakdown_response import EpicBreakdownResponse
from .analysis_info import AnalysisInfo

class JiraEpicBreakdownResult(EpicBreakdownResponse):
    """Legacy model that inherits from EpicBreakdownResponse for backward compatibility.
    
    @deprecated: Use EpicBreakdownResponse directly instead.
    This class exists only for backward compatibility and will be removed in a future version.
    """
    # Override tasks to allow raw dict for backward compatibility
    tasks: List[Dict[str, Any]]
    analysis: AnalysisInfo 