from typing import Dict, Any, Set
from loguru import logger
from services.task_tracker import TaskTracker
from services.execution_log_service import ExecutionLogService

def log_completion_summary(task_tracker: TaskTracker, execution_log: ExecutionLogService) -> None:
    """
    Generate and log a detailed completion summary of the breakdown process.
    
    Args:
        task_tracker: TaskTracker instance with final state
        execution_log: ExecutionLogService instance for logging
    """
    try:
        # Get summary statistics
        summary = task_tracker.get_summary()
        total_tasks = summary['user_stories'] + summary['technical_tasks']
        total_subtasks = summary['subtasks']
        
        # Calculate additional statistics
        total_story_points = 0
        skills_required: Set[str] = set()
        max_subtasks = 0
        min_subtasks = float('inf') if total_tasks > 0 else 0
        
        for parent, subtasks in task_tracker.subtasks.items():
            subtask_count = len(subtasks)
            max_subtasks = max(max_subtasks, subtask_count)
            min_subtasks = min(min_subtasks, subtask_count)
            
            for subtask in subtasks:
                total_story_points += subtask.get('story_points', 0)
                skills_required.update(subtask.get('required_skills', []))
        
        # Calculate averages
        avg_subtasks = total_subtasks/total_tasks if total_tasks > 0 else 0
        avg_points = total_story_points/total_subtasks if total_subtasks > 0 else 0
        estimated_days = total_story_points/5 if total_story_points > 0 else 0
        
        # Format summary
        completion_summary = (
            f"\nTask Breakdown Completion Report\n"
            f"===============================\n\n"
            f"High-Level Tasks:\n"
            f"- Total tasks processed: {total_tasks}\n"
            f"- User Stories: {summary['user_stories']}\n"
            f"- Technical Tasks: {summary['technical_tasks']}\n\n"
            
            f"Subtask Statistics:\n"
            f"- Total subtasks created: {total_subtasks}\n"
            f"- Average subtasks per task: {avg_subtasks:.1f}\n"
            f"- Most subtasks for a task: {max_subtasks}\n"
            f"- Least subtasks for a task: {min_subtasks}\n\n"
            
            f"Effort Estimation:\n"
            f"- Total story points: {total_story_points}\n"
            f"- Average points per subtask: {avg_points:.1f}\n"
            f"- Estimated total effort: {estimated_days:.1f} days\n\n"
            
            f"Technical Requirements:\n"
            f"- Required skills: {', '.join(sorted(skills_required))}\n\n"
            
            f"Breakdown by Parent Task:\n"
        )
        
        # Add per-task breakdown
        for parent, count in summary['subtasks_by_parent'].items():
            parent_subtasks = task_tracker.subtasks.get(parent, [])
            parent_points = sum(subtask.get('story_points', 0) for subtask in parent_subtasks)
            completion_summary += (
                f"- {parent}:\n"
                f"  • Subtasks: {count}\n"
                f"  • Story Points: {parent_points}\n"
                f"  • Required Skills: {', '.join(sorted(set(skill for subtask in parent_subtasks for skill in subtask.get('required_skills', []))))}\n"
            )
        
        # Log the summary
        logger.info(completion_summary)
        execution_log.log_section("Task Breakdown Completion", completion_summary)
        
    except Exception as e:
        logger.error(f"Failed to generate completion summary: {str(e)}")
        raise 