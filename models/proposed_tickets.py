from pydantic import BaseModel
from typing import Dict, List, Any
from .jira_task_definition import JiraTaskDefinition

class ProposedTickets(BaseModel):
    file: str
    summary: Dict[str, Any]
    high_level_tasks: List[JiraTaskDefinition]
    subtasks_by_parent: Dict[str, int] 