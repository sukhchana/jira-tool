from pydantic import BaseModel
from typing import List
from .high_level_task import HighLevelTask
from .sub_task import SubTask

class TaskGroup(BaseModel):
    """Model representing a group of related tasks"""
    high_level_task: HighLevelTask
    subtasks: List[SubTask] 