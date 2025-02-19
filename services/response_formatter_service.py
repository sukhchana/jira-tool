from typing import Dict, Any, List
from models import (
    JiraEpicBreakdownResult,
    BreakdownInfo,
    MetricsInfo,
    ExecutionPlanStats,
    ProposedTickets,
    JiraTaskDefinition
)
from models.sub_task import SubTask
from loguru import logger

class ResponseFormatterService:
    """Service for formatting API responses"""
    
    @staticmethod
    def format_epic_breakdown(result: Dict[str, Any]) -> JiraEpicBreakdownResult:
        """Format epic breakdown response"""
        try:
            # Convert tasks to proper format
            formatted_tasks = []
            for task in result["tasks"]:
                task_dict = {
                    "high_level_task": task["high_level_task"],
                    "subtasks": [
                        subtask.dict() if isinstance(subtask, SubTask) else subtask
                        for subtask in task.get("subtasks", [])
                    ]
                }
                formatted_tasks.append(task_dict)
            
            # Create execution plan stats
            execution_plan = ExecutionPlanStats(
                user_stories=len([t for t in formatted_tasks if t["high_level_task"]["type"] == "User Story"]),
                technical_tasks=len([t for t in formatted_tasks if t["high_level_task"]["type"] == "Technical Task"]),
                total_subtasks=sum(len(t.get("subtasks", [])) for t in formatted_tasks)
            )
            
            # Create proposed tickets
            proposed_tickets = ProposedTickets(
                file=result["proposed_tickets_file"],
                summary={
                    "total_tasks": len(formatted_tasks),
                    "total_subtasks": sum(len(t.get("subtasks", [])) for t in formatted_tasks),
                    "task_types": {
                        "user_stories": len([t for t in formatted_tasks if t["high_level_task"]["type"] == "User Story"]),
                        "technical_tasks": len([t for t in formatted_tasks if t["high_level_task"]["type"] == "Technical Task"])
                    }
                },
                high_level_tasks=[
                    JiraTaskDefinition(
                        id=task["high_level_task"].get("id") or f"TASK-{i+1}",
                        type=task["high_level_task"]["type"],
                        title=task["high_level_task"]["title"],
                        complexity=task["high_level_task"]["complexity"]
                    )
                    for i, task in enumerate(formatted_tasks)
                ],
                subtasks_by_parent={
                    task["high_level_task"]["title"]: len(task.get("subtasks", []))
                    for task in formatted_tasks
                }
            )
            
            return JiraEpicBreakdownResult(
                execution_id=result["execution_id"],
                epic_key=result["epic_key"],
                epic_summary=result["epic_summary"],
                analysis=result["analysis"],
                tasks=formatted_tasks,
                execution_plan_file=result["execution_plan_file"],
                proposed_tickets_file=result["proposed_tickets_file"],
                breakdown=BreakdownInfo(
                    execution_plan=execution_plan,
                    proposed_tickets=proposed_tickets
                ),
                metrics=MetricsInfo(
                    total_story_points=sum(
                        subtask["story_points"] if isinstance(subtask, dict) else subtask.story_points
                        for task in formatted_tasks
                        for subtask in task.get("subtasks", [])
                    ),
                    estimated_days=sum(
                        subtask["story_points"] if isinstance(subtask, dict) else subtask.story_points
                        for task in formatted_tasks
                        for subtask in task.get("subtasks", [])
                    ) / 5,
                    required_skills=sorted(list(set(
                        skill
                        for task in formatted_tasks
                        for subtask in task.get("subtasks", [])
                        for skill in (subtask["required_skills"] if isinstance(subtask, dict) else subtask.required_skills)
                    )))
                )
            )
        except Exception as e:
            logger.error(f"Failed to format epic breakdown response: {str(e)}")
            logger.error(f"Result data: {result}")
            raise 