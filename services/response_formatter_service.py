from typing import Dict, Any
from models import (
    JiraEpicBreakdownResult,
    EpicInfo,
    AnalysisInfo,
    BreakdownInfo,
    MetricsInfo,
    JiraTaskDefinition
)
from loguru import logger

class ResponseFormatterService:
    """Service for formatting API responses"""
    
    @staticmethod
    def format_epic_breakdown(result: Dict[str, Any]) -> JiraEpicBreakdownResult:
        """Format epic breakdown response"""
        try:
            return JiraEpicBreakdownResult(
                epic=EpicInfo(
                    key=result["epic_key"],
                    summary=result["epic_summary"]
                ),
                analysis=AnalysisInfo(
                    main_objective=result["analysis"].get("main_objective", ""),
                    technical_domains=result["analysis"].get("technical_domains", []),
                    core_requirements=result["analysis"].get("core_requirements", []),
                    stakeholders=result["analysis"].get("stakeholders", [])
                ),
                breakdown=BreakdownInfo(
                    execution_plan={
                        "user_stories": len([t for t in result["tasks"] if t["high_level_task"]["type"] == "User Story"]),
                        "technical_tasks": len([t for t in result["tasks"] if t["high_level_task"]["type"] == "Technical Task"]),
                        "total_subtasks": sum(len(t.get("subtasks", [])) for t in result["tasks"])
                    },
                    proposed_tickets={
                        "file": result["proposed_tickets_file"],
                        "summary": {
                            "total_tasks": len(result["tasks"]),
                            "total_subtasks": sum(len(t.get("subtasks", [])) for t in result["tasks"]),
                            "task_types": {
                                "user_stories": len([t for t in result["tasks"] if t["high_level_task"]["type"] == "User Story"]),
                                "technical_tasks": len([t for t in result["tasks"] if t["high_level_task"]["type"] == "Technical Task"])
                            }
                        },
                        "high_level_tasks": [
                            {
                                "id": task["high_level_task"].get("id") or f"TASK-{i+1}",
                                "type": task["high_level_task"]["type"],
                                "name": task["high_level_task"]["name"],
                                "complexity": task["high_level_task"]["complexity"]
                            }
                            for i, task in enumerate(result["tasks"])
                        ],
                        "subtasks_by_parent": {
                            task["high_level_task"]["name"]: len(task.get("subtasks", []))
                            for task in result["tasks"]
                        }
                    }
                ),
                metrics=MetricsInfo(
                    total_story_points=sum(
                        subtask.get("story_points", 0)
                        for task in result["tasks"]
                        for subtask in task.get("subtasks", [])
                    ),
                    estimated_days=sum(
                        subtask.get("story_points", 0)
                        for task in result["tasks"]
                        for subtask in task.get("subtasks", [])
                    ) / 5,
                    required_skills=sorted(list(set(
                        skill
                        for task in result["tasks"]
                        for subtask in task.get("subtasks", [])
                        for skill in subtask.get("required_skills", [])
                    )))
                )
            )
        except Exception as e:
            logger.error(f"Failed to format epic breakdown response: {str(e)}")
            raise 