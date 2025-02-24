from pydantic import BaseModel


class ExecutionPlanStats(BaseModel):
    user_stories: int
    technical_tasks: int
    total_subtasks: int
