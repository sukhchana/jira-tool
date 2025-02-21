from typing import Dict, Any, List, Union
from models import (
    JiraEpicBreakdownResult,
    BreakdownInfo,
    MetricsInfo,
    ExecutionPlanStats,
    ProposedTickets,
    JiraTaskDefinition,
    EpicBreakdownResponse,
    SubTask
)
from loguru import logger
import json

class ResponseFormatterService:
    """Service for formatting API responses"""
    
    @staticmethod
    def format_epic_breakdown(result: Union[Dict[str, Any], EpicBreakdownResponse]) -> JiraEpicBreakdownResult:
        """Format epic breakdown response"""
        try:
            logger.debug("Starting to format epic breakdown response")
            
            # Convert EpicBreakdownResponse to dict if needed
            if isinstance(result, EpicBreakdownResponse):
                result = result.model_dump()
            
            logger.debug(f"Input result keys: {list(result.keys())}")
            
            # Log the raw input for debugging
            try:
                logger.debug("Raw input data:")
                logger.debug(json.dumps(result, default=str))
            except Exception as e:
                logger.error(f"Failed to serialize raw input: {str(e)}")
                logger.debug("Individual field inspection:")
                for key, value in result.items():
                    try:
                        json.dumps({key: value}, default=str)
                    except Exception as e:
                        logger.error(f"Field '{key}' is not serializable: {str(e)}")
                        logger.error(f"Type of '{key}': {type(value)}")
                        if hasattr(value, '__dict__'):
                            logger.error(f"Attributes of '{key}': {vars(value)}")

            # Convert tasks to proper format
            formatted_tasks = []
            for task in result["tasks"]:
                try:
                    # Log the task structure for debugging
                    logger.debug(f"Processing task: {task}")
                    if not isinstance(task, dict):
                        logger.error(f"Task is not a dictionary: {type(task)}")
                        continue
                        
                    # Verify high_level_task exists and has required fields
                    high_level_task = task.get("high_level_task")
                    if not high_level_task:
                        logger.error(f"Task missing high_level_task field: {task}")
                        continue
                        
                    if not isinstance(high_level_task, dict):
                        logger.error(f"high_level_task is not a dictionary: {type(high_level_task)}")
                        continue
                        
                    required_fields = ["type", "title", "complexity"]
                    missing_fields = [f for f in required_fields if f not in high_level_task]
                    if missing_fields:
                        logger.error(f"high_level_task missing required fields {missing_fields}: {high_level_task}")
                        continue

                    task_dict = {
                        "high_level_task": high_level_task,
                        "subtasks": [
                            subtask.dict() if isinstance(subtask, SubTask) else subtask
                            for subtask in task.get("subtasks", [])
                        ]
                    }
                    formatted_tasks.append(task_dict)
                except Exception as e:
                    logger.error(f"Failed to format task: {str(e)}")
                    logger.error(f"Task data: {task}")
                    logger.error("Task structure:")
                    for key, value in task.items():
                        logger.error(f"  {key}: {type(value)}")
                    raise
            
            if not formatted_tasks:
                raise ValueError("No valid tasks were processed")
            
            logger.debug(f"Formatted {len(formatted_tasks)} tasks")
            
            # Create execution plan stats
            execution_plan = ExecutionPlanStats(
                user_stories=len([t for t in formatted_tasks if t["high_level_task"]["type"] == "User Story"]),
                technical_tasks=len([t for t in formatted_tasks if t["high_level_task"]["type"] == "Technical Task"]),
                total_subtasks=sum(len(t.get("subtasks", [])) for t in formatted_tasks)
            )
            
            logger.debug("Created execution plan stats")
            
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
            
            logger.debug("Created proposed tickets")
            
            # Create final response
            response = JiraEpicBreakdownResult(
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
            
            # Verify serialization before returning
            try:
                logger.debug("Testing response serialization")
                json.dumps(response.dict(), default=str)
                logger.debug("Response serialization successful")
            except Exception as e:
                logger.error(f"Response serialization failed: {str(e)}")
                logger.error("Inspecting response fields:")
                for key, value in response.dict().items():
                    try:
                        json.dumps({key: value}, default=str)
                    except Exception as e:
                        logger.error(f"Field '{key}' is not serializable: {str(e)}")
                        logger.error(f"Type of '{key}': {type(value)}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to format epic breakdown response: {str(e)}")
            logger.error(f"Result data structure: {type(result)}")
            logger.error("Available keys in result:")
            for key in result.keys():
                logger.error(f"- {key}: {type(result[key])}")
            raise 