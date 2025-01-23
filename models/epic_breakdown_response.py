from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from .task_group import TaskGroup

class EpicBreakdownResponse(BaseModel):
    """Response model containing the complete epic breakdown"""
    epic_key: str
    epic_summary: str
    analysis: Dict[str, Any]
    tasks: List[TaskGroup]
    created_jira_tasks: Optional[List[Dict[str, Any]]] = None
    execution_plan: Optional[str] = None 