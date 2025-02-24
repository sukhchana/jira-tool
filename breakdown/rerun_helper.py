from typing import Union

from loguru import logger

from breakdown.breakdown_summary_logger import log_completion_summary
from breakdown.execution_manager import ExecutionManager
from models.analysis_info import AnalysisInfo
from models.breakdown_info import BreakdownInfo
from models.epic_breakdown_response import EpicBreakdownResponse
from models.execution_plan_stats import ExecutionPlanStats
from models.high_level_task import HighLevelTask
from models.jira_task_definition import JiraTaskDefinition
from models.jira_ticket_details import JiraTicketDetails
from models.metrics_info import MetricsInfo
from models.proposed_tickets import ProposedTickets
from models.task_group import TaskGroup
from models.technical_task import TechnicalTask
from models.user_story import UserStory
from services.task_tracker import TaskTracker


class RerunHelper:
    """Helper class for rerunning parts of the epic breakdown process"""

    @staticmethod
    def _to_high_level_task(task: Union[UserStory, TechnicalTask]) -> HighLevelTask:
        """Convert a UserStory or TechnicalTask to a HighLevelTask
        
        Args:
            task: The UserStory or TechnicalTask to convert
            
        Returns:
            HighLevelTask representation of the input task
        """
        return HighLevelTask(
            title=task.title,
            type="User Story" if isinstance(task, UserStory) else "Technical Task",
            description=task.description,
            technical_domain=task.technical_domain,
            complexity=task.complexity,
            dependencies=task.dependencies
        )

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
                        execution_plan=ExecutionPlanStats(
                            user_stories=len(user_stories),
                            technical_tasks=len(technical_tasks),
                            total_subtasks=len(all_subtasks)
                        ),
                        proposed_tickets=ProposedTickets(
                            file=execution_manager.proposed_tickets.filename,
                            summary={
                                "total_tasks": len(user_stories) + len(technical_tasks),
                                "total_subtasks": len(all_subtasks),
                                "task_types": {
                                    "user_stories": len(user_stories),
                                    "technical_tasks": len(technical_tasks)
                                }
                            },
                            high_level_tasks=[
                                JiraTaskDefinition(
                                    id=task.id,
                                    type="User Story" if isinstance(task, UserStory) else "Technical Task",
                                    title=task.title,
                                    complexity=task.complexity
                                )
                                for task in (user_stories + technical_tasks)
                            ],
                            subtasks_by_parent={
                                task.title: len([st for st in all_subtasks if st.parent_id == task.id])
                                for task in (user_stories + technical_tasks)
                            }
                        )
                    ),
                    metrics=MetricsInfo(
                        total_story_points=sum(subtask.story_points for subtask in all_subtasks),
                        estimated_days=sum(subtask.story_points for subtask in all_subtasks) / 5,
                        # Assuming 5 points per day
                        required_skills=list(set(
                            skill
                            for subtask in all_subtasks
                            for skill in subtask.required_skills
                        ))
                    ),
                    tasks=[
                        TaskGroup(
                            high_level_task=cls._to_high_level_task(task),
                            subtasks=[st for st in all_subtasks if st.parent_id == task.id]
                        )
                        for task in (user_stories + technical_tasks)
                    ],
                    execution_plan_file=execution_manager.execution_log.filename,
                    proposed_tickets_file=execution_manager.proposed_tickets.filename
                )

                # Save final state
                execution_manager._save_state("final_result.json", response.model_dump())
                execution_manager.proposed_tickets.save()

                # Log completion summary
                log_completion_summary(task_tracker, execution_manager.execution_log)

                return response

            except Exception as e:
                cls._handle_task_generation_error(e, task_tracker, epic_analysis)
                raise

        except Exception as e:
            cls._handle_fatal_error(e)
            raise

    @staticmethod
    def _handle_task_generation_error(
            error: Exception,
            task_tracker: TaskTracker,
            epic_analysis: AnalysisInfo
    ) -> None:
        """Handle errors during task generation"""
        logger.error(f"Task generation error: {str(error)}")
        logger.error(f"Epic analysis: {epic_analysis.model_dump()}")
        logger.error(f"Task tracker state: {task_tracker.get_all_tasks()}")
        logger.exception("Full traceback:")

    @staticmethod
    def _handle_fatal_error(error: Exception) -> None:
        """Handle fatal errors during execution"""
        logger.error(f"Fatal error occurred: {str(error)}")
        logger.exception("Full traceback:")
