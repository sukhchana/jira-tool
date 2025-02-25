from pydantic import BaseModel, Field


class JiraEpicProgress(BaseModel):
    """Model representing progress statistics for a JIRA epic"""
    total_issues: int = Field(..., description="Total number of issues linked to the epic")
    completed_issues: int = Field(..., description="Number of issues in a 'done' state")
    completion_percentage: float = Field(..., description="Percentage of completed issues")
    stories_count: int = Field(..., description="Number of story issues in the epic")
    tasks_count: int = Field(..., description="Number of task issues in the epic")
    subtasks_count: int = Field(..., description="Number of subtask issues in the epic")
    done_issues: int = Field(..., description="Number of issues marked as done") 