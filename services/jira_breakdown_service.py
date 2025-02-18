from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from services.jira_service import JiraService
from llm.vertexllm import VertexLLM
from loguru import logger
from breakdown import ExecutionManager

class JiraBreakdownService:
    """
    Service responsible for orchestrating the breakdown of JIRA epics into smaller tasks.
    
    This service has been refactored to use the breakdown package components for better
    separation of concerns and maintainability.
    """

    def __init__(self, epic_key: str):
        """Initialize the breakdown service with dependencies"""
        self.epic_key = epic_key
        self.execution_manager = ExecutionManager(epic_key)
        logger.info("Successfully initialized JiraBreakdownService")

    async def break_down_epic(self) -> Dict[str, Any]:
        """Break down a JIRA epic into smaller tasks"""
        return await self.execution_manager.execute_breakdown()

    async def create_epic_subtasks(self, breakdown: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create JIRA tickets for all subtasks in the epic breakdown.
        
        Args:
            breakdown: The epic breakdown structure
            
        Returns:
            List of created JIRA tickets
        """
        try:
            logger.info(f"Creating JIRA tickets for epic {self.epic_key}")
            created_tasks = []
            project_key = self.epic_key.split("-")[0]

            for task_group in breakdown["tasks"]:
                # Create a story for the high-level task
                high_level_task = task_group["high_level_task"]
                story = await self.execution_manager.jira.create_ticket({
                    "project_key": project_key,
                    "summary": high_level_task["title"],
                    "description": (
                        f"{high_level_task['description']}\n\n"
                        f"Technical Domain: {high_level_task['technical_domain']}\n"
                        f"Complexity: {high_level_task['complexity']}\n"
                        f"Dependencies: {', '.join(high_level_task['dependencies'])}"
                    ),
                    "issue_type": "Story",
                    "parent_key": self.epic_key  # Link to parent epic
                })
                created_tasks.append(story)

                # Create subtasks
                for subtask in task_group["subtasks"]:
                    task = await self.execution_manager.jira.create_ticket({
                        "project_key": project_key,
                        "summary": subtask["title"],
                        "description": (
                            f"{subtask['description']}\n\n"
                            f"Acceptance Criteria:\n{subtask['acceptance_criteria']}\n\n"
                            f"Required Skills: {', '.join(subtask['required_skills'])}\n"
                            f"Story Points: {subtask['story_points']}\n"
                            f"Suggested Assignee Type: {subtask['suggested_assignee']}"
                        ),
                        "issue_type": "Sub-task",
                        "parent_key": story["key"],  # Link to parent story
                        "story_points": subtask["story_points"],
                        "labels": subtask["required_skills"]
                    })
                    created_tasks.append(task)

            logger.success(f"Successfully created {len(created_tasks)} JIRA tickets")
            return created_tasks

        except Exception as e:
            logger.error(f"Failed to create JIRA tickets: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create JIRA tickets: {str(e)}"
            )

    def _create_ticket_data(self, high_level_task: Dict[str, Any]) -> Dict[str, Any]:
        """Create ticket data from high level task"""
        return {
            "type": high_level_task.get("type", "Task"),
            "summary": high_level_task["title"],
            "description": high_level_task.get("description", ""),
            "technical_domain": high_level_task.get("technical_domain", ""),
            "complexity": high_level_task.get("complexity", "Medium"),
            "dependencies": high_level_task.get("dependencies", [])
        } 