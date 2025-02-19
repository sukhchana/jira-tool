from typing import List, Dict, Any
from loguru import logger
from pathlib import Path
from models.epic_breakdown_response import EpicBreakdownResponse
from models.jira_ticket_details import JiraTicketDetails
from models.analysis_info import AnalysisInfo
from models.user_story import UserStory
from models.technical_task import TechnicalTask
from models.sub_task import SubTask
from services.task_tracker import TaskTracker
from breakdown.execution_manager import ExecutionManager
from breakdown.breakdown_summary_logger import log_completion_summary
from models.breakdown_info import BreakdownInfo
from models.metrics_info import MetricsInfo
import json

class RerunHelper:
    """Helper class for rerunning parts of the epic breakdown process"""
    
    @classmethod
    async def rerun_subtask_generation(
        cls,
        epic_key: str,
        source_execution_id: str
    ) -> EpicBreakdownResponse:
        """
        Rerun subtask generation using state from a previous execution.
        
        This method:
        1. Creates a new execution with a new ID
        2. Loads the epic details, analysis, and high-level tasks from the source execution
        3. Regenerates subtasks for all high-level tasks
        4. Returns a new EpicBreakdownResponse with the updated results
        
        Args:
            epic_key: The JIRA key of the epic
            source_execution_id: The execution ID to load state from
            
        Returns:
            A new EpicBreakdownResponse with regenerated subtasks
            
        Raises:
            FileNotFoundError: If source execution state files are not found
            ValueError: If required state data is missing or invalid
        """
        # Create new execution manager with new ID
        execution_manager = ExecutionManager(epic_key)
        logger.info(f"Created new execution {execution_manager.execution_id} based on {source_execution_id}")
        
        try:
            # Load required state from source execution using ExecutionManager's method
            epic_details = JiraTicketDetails(**ExecutionManager.load_execution_state(
                epic_key, source_execution_id, "epic_details.json"
            ))
            epic_analysis = AnalysisInfo(**ExecutionManager.load_execution_state(
                epic_key, source_execution_id, "epic_analysis.json"
            ))
            
            # Load high-level tasks
            user_stories_data = ExecutionManager.load_execution_state(
                epic_key, source_execution_id, "user_stories.json"
            )
            technical_tasks_data = ExecutionManager.load_execution_state(
                epic_key, source_execution_id, "technical_tasks.json"
            )
            
            user_stories = [UserStory(**story) for story in user_stories_data]
            technical_tasks = [TechnicalTask(**task) for task in technical_tasks_data]
            
            logger.info(f"Loaded {len(user_stories)} user stories and {len(technical_tasks)} technical tasks")
            
            # Initialize services
            task_tracker = TaskTracker(epic_key)
            
            try:
                # Generate subtasks for user stories
                user_story_subtasks = await execution_manager.generate_subtasks(
                    user_stories,
                    epic_details,
                    task_tracker,
                    "user_story"
                )
                logger.info(f"Generated {len(user_story_subtasks)} subtasks for user stories")
                
                # Generate subtasks for technical tasks
                technical_task_subtasks = await execution_manager.generate_subtasks(
                    technical_tasks,
                    epic_details,
                    task_tracker,
                    "technical_task"
                )
                logger.info(f"Generated {len(technical_task_subtasks)} subtasks for technical tasks")
                
                # Create response with combined tasks
                all_subtasks = user_story_subtasks + technical_task_subtasks
                
                response = EpicBreakdownResponse(
                    execution_id=execution_manager.execution_id,
                    epic_key=epic_key,
                    epic_summary=epic_details.summary,
                    analysis=epic_analysis,
                    breakdown=BreakdownInfo(
                        execution_plan={
                            "user_stories": [story.dict() for story in user_stories],
                            "technical_tasks": [task.dict() for task in technical_tasks]
                        },
                        proposed_tickets={
                            "user_story_subtasks": [subtask.dict() for subtask in user_story_subtasks],
                            "technical_task_subtasks": [subtask.dict() for subtask in technical_task_subtasks],
                            "total_count": len(all_subtasks),
                            "total_story_points": sum(subtask.story_points for subtask in all_subtasks)
                        }
                    ),
                    metrics=MetricsInfo(
                        total_story_points=sum(subtask.story_points for subtask in all_subtasks),
                        estimated_days=sum(subtask.story_points for subtask in all_subtasks) / 5,  # Assuming 5 points per day
                        required_skills=list(set(
                            skill
                            for subtask in all_subtasks
                            for skill in subtask.required_skills
                        ))
                    ),
                    tasks=[{
                        "high_level_task": task.dict(),
                        "subtasks": [
                            st for st in (user_story_subtasks if isinstance(task, UserStory) else technical_task_subtasks)
                            if st.parent_id == task.id
                        ]
                    } for task in user_stories + technical_tasks],
                    execution_plan_file=execution_manager.execution_log.filename,
                    proposed_tickets_file=execution_manager.proposed_tickets.filename
                )
                
                # Save final state
                execution_manager._save_state("final_result.json", response.dict())
                execution_manager.proposed_tickets.save()
                
                # Log completion summary
                log_completion_summary(task_tracker, execution_manager.execution_log)
                
                return response
                
            except Exception as e:
                execution_manager._handle_task_generation_error(e, task_tracker, epic_analysis)
                raise
                
        except Exception as e:
            execution_manager._handle_fatal_error(e)
            raise 