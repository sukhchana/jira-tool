from typing import Dict, Any, List, Union
from loguru import logger
from fastapi import HTTPException
from breakdown.breakdown_summary_logger import log_completion_summary
from services.jira_service import JiraService
from services.execution_log_service import ExecutionLogService
from services.task_tracker import TaskTracker
from services.proposed_tickets_service import ProposedTicketsService
from .epic_analyzer import EpicAnalyzer
from .user_story_generator import UserStoryGenerator
from .technical_task_generator import TechnicalTaskGenerator
from .subtask_generator import SubtaskGenerator
from models.user_story import UserStory
from models.technical_task import TechnicalTask
from uuid_extensions import uuid7

class ExecutionManager:
    """
    Service responsible for coordinating the epic breakdown process.
    
    This service orchestrates the interaction between:
    - EpicAnalyzer for analyzing epics
    - UserStoryGenerator for generating user stories
    - TechnicalTaskGenerator for generating technical tasks
    - SubtaskGenerator for breaking down tasks into subtasks
    - Various tracking and logging services
    """
    
    def __init__(self, epic_key: str):
        """Initialize the execution manager with dependencies"""
        self.epic_key = epic_key
        self.execution_id = str(uuid7())
        
        # Initialize services
        self.execution_log = ExecutionLogService(epic_key)
        self.proposed_tickets = ProposedTicketsService(epic_key=epic_key, execution_id=self.execution_id)
        self.jira = JiraService()
        
        # Initialize breakdown components
        self.epic_analyzer = EpicAnalyzer(self.execution_log)
        self.user_story_generator = UserStoryGenerator(self.execution_log)
        self.technical_task_generator = TechnicalTaskGenerator(self.execution_log)
        self.subtask_generator = SubtaskGenerator(self.execution_log)
        
        logger.info(f"Initialized ExecutionManager for epic {epic_key}")
    
    async def execute_breakdown(self) -> Dict[str, Any]:
        """
        Execute the epic breakdown process.
        
        Returns:
            Dict containing breakdown results and execution details
        """
        task_tracker = TaskTracker(self.epic_key)
        
        try:
            logger.info(f"Starting breakdown for epic: {self.epic_key}")
            
            # Get epic details from JIRA
            epic_details = await self.jira.get_ticket(self.epic_key)
            if not epic_details:
                raise ValueError(f"Epic {self.epic_key} not found")
            
            # Analyze epic
            epic_analysis = await self.epic_analyzer.analyze_epic(
                epic_details["summary"],
                epic_details["description"]
            )
            
            try:
                # Generate high-level tasks
                all_tasks: List[Union[UserStory, TechnicalTask]] = []
                
                # First generate user stories
                user_stories = await self.user_story_generator.generate_user_stories(
                    epic_analysis,
                    task_tracker,
                    self.proposed_tickets
                )
                all_tasks.extend(user_stories)
                
                # Generate subtasks for user stories
                await self.subtask_generator.break_down_tasks(
                    user_stories,
                    epic_details,
                    task_tracker,
                    self.proposed_tickets
                )
                
                # Then generate technical tasks based on the user stories
                technical_tasks = await self.technical_task_generator.generate_technical_tasks(
                    user_stories,
                    epic_analysis,
                    task_tracker,
                    self.proposed_tickets
                )
                all_tasks.extend(technical_tasks)
                
                # Generate subtasks for technical tasks
                await self.subtask_generator.break_down_tasks(
                    technical_tasks,
                    epic_details,
                    task_tracker,
                    self.proposed_tickets
                )
                
                # Log completion summary after all tasks are broken down
                log_completion_summary(task_tracker, self.execution_log)
                
                # Debug log task tracker state
                logger.debug("Task tracker state after breakdown:")
                logger.debug(task_tracker.debug_state())
                
                # Save the proposed tickets
                self.proposed_tickets.save()
                
                # Save successful execution record
                await self.execution_log.create_execution_record(
                    execution_id=self.execution_id,
                    epic_key=self.epic_key,
                    execution_plan_file=self.execution_log.filename,
                    proposed_plan_file=self.proposed_tickets.filename,
                    status="SUCCESS"
                )
                
                return {
                    "execution_id": self.execution_id,
                    "epic_key": self.epic_key,
                    "epic_summary": epic_details["summary"],
                    "analysis": epic_analysis,
                    "tasks": task_tracker.get_all_tasks(),
                    "execution_plan_file": self.execution_log.filename,
                    "proposed_tickets_file": self.proposed_tickets.filename
                }
                
            except Exception as e:
                # Handle task generation/breakdown errors
                error_summary = task_tracker.get_summary()
                error_summary["errors"] = [str(e)]
                self.execution_log.log_summary(error_summary)
                
                # Save failed execution record
                await self.execution_log.create_execution_record(
                    execution_id=self.execution_id,
                    epic_key=self.epic_key,
                    execution_plan_file=self.execution_log.filename,
                    proposed_plan_file=self.proposed_tickets.filename,
                    status="FAILED"
                )
                
                logger.error(f"Failed during task generation/breakdown: {str(e)}")
                logger.error("Tasks structure at time of error:")
                logger.error(task_tracker.get_all_tasks())
                logger.error(f"Epic analysis that caused error:\n{epic_analysis}")
                
                return {
                    "epic_key": self.epic_key,
                    "epic_summary": epic_details["summary"],
                    "analysis": epic_analysis,
                    "error": str(e),
                    "tasks": [],
                    "execution_id": self.execution_id,
                    "status": "FAILED",
                    "execution_plan_file": self.execution_log.filename,
                    "proposed_tickets_file": self.proposed_tickets.filename
                }
                
        except Exception as e:
            # Handle fatal errors during setup or epic retrieval
            self.execution_log.log_section("Fatal Error", str(e))
            
            # Save fatal error execution record
            await self.execution_log.create_execution_record(
                execution_id=self.execution_id,
                epic_key=self.epic_key,
                execution_plan_file=self.execution_log.filename,
                proposed_plan_file="",  # No proposed tickets in fatal error
                status="FATAL_ERROR"
            )
            
            logger.error(f"Fatal error during epic breakdown: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to break down epic: {str(e)}"
            ) 