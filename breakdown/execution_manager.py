import json
from pathlib import Path
from typing import Any, List, Union, Tuple
import asyncio
import os

from loguru import logger
from uuid_extensions import uuid7

from breakdown.breakdown_summary_logger import log_completion_summary
from models.analysis_info import AnalysisInfo
from models.breakdown_info import BreakdownInfo
from models.epic_breakdown_response import EpicBreakdownResponse
from models.execution_plan_stats import ExecutionPlanStats
from models.jira_task_definition import JiraTaskDefinition
from models.jira_ticket_details import JiraTicketDetails
from models.metrics_info import MetricsInfo
from models.proposed_tickets import ProposedTickets
from models.sub_task import SubTask
from models.technical_task import TechnicalTask
from models.user_story import UserStory
from services.execution_log_service import ExecutionLogService
from jira_integration.jira_service import JiraService
from services.proposed_tickets_service import ProposedTicketsService
from services.task_tracker import TaskTracker
from services.metrics_service import EpicBreakdownTracker
from utils.config import Settings
from .epic_analyzer import EpicAnalyzer
from .subtask_generator import SubtaskGenerator
from .technical_task_generator import TechnicalTaskGenerator
from .user_story_generator import UserStoryGenerator
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from functools import partial
from services.mongodb_service import MongoDBService


class ExecutionManager:
    """
    Service responsible for coordinating the epic breakdown process.
    
    This service orchestrates the interaction between various components to break down
    an epic into smaller, manageable tasks. It handles the entire workflow from epic
    analysis to subtask generation, while maintaining execution state and error handling.

    Components:
        - EpicAnalyzer: Analyzes epic content and requirements
        - UserStoryGenerator: Generates user stories from epic analysis
        - TechnicalTaskGenerator: Creates technical tasks based on user stories
        - SubtaskGenerator: Breaks down high-level tasks into subtasks
        - Various tracking and logging services for monitoring progress

    Attributes:
        epic_key (str): The JIRA key of the epic being broken down
        execution_id (str): Unique identifier for this execution
        state_dir (Path): Directory where execution state files are stored
    """

    def __init__(self, epic_key: str):
        """
        Initialize the execution manager with required dependencies.

        Args:
            epic_key: The JIRA key of the epic to break down (e.g., 'PROJ-123')
        """
        self.epic_key = epic_key
        self.execution_id = str(uuid7())
        self.state_dir = Path(f"execution_states/{self.epic_key}/{self.execution_id}")
        self.state_dir.mkdir(parents=True, exist_ok=True)

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

    async def analyze_epic_details(self) -> Tuple[JiraTicketDetails, AnalysisInfo]:
        """
        Retrieve epic details from JIRA and perform initial analysis.

        This method:
        1. Fetches the epic's details from JIRA
        2. Analyzes the epic's content using the EpicAnalyzer
        3. Saves both the epic details and analysis to the execution state

        Returns:
            A tuple containing:
                - JiraTicketDetails: The epic's details from JIRA
                - AnalysisInfo: Structured analysis of the epic's content

        Raises:
            ValueError: If the epic is not found in JIRA
            Exception: If analysis fails or state cannot be saved
        """
        epic_details = await self.jira.get_ticket(self.epic_key)
        if not epic_details:
            raise ValueError(f"Epic {self.epic_key} not found")

        epic_analysis = await self.epic_analyzer.analyze_epic(
            epic_details.summary,
            epic_details.description
        )

        self._save_state("epic_details.json", epic_details.model_dump())
        self._save_state("epic_analysis.json", epic_analysis.model_dump())

        return epic_details, epic_analysis

    async def generate_user_stories(
            self,
            epic_analysis: AnalysisInfo,
            task_tracker: TaskTracker
    ) -> List[UserStory]:
        """
        Generate user stories based on epic analysis.

        This method uses the UserStoryGenerator to create a list of user stories
        that capture the requirements and objectives identified in the epic analysis.
        The generated stories are tracked and saved to the execution state.

        Args:
            epic_analysis: Structured analysis of the epic's content
            task_tracker: Service for tracking generated tasks

        Returns:
            List of generated UserStory objects

        Raises:
            Exception: If story generation fails or state cannot be saved
        """
        user_stories = await self.user_story_generator.generate_user_stories(
            epic_analysis.model_dump(),
            task_tracker,
            self.proposed_tickets
        )

        self._save_state("user_stories.json", [story.model_dump() for story in user_stories])
        return user_stories

    async def generate_technical_tasks(
            self,
            user_stories: List[UserStory],
            epic_analysis: AnalysisInfo,
            task_tracker: TaskTracker
    ) -> List[TechnicalTask]:
        """
        Generate technical tasks based on user stories and epic analysis.

        This method creates technical implementation tasks that support the
        requirements defined in the user stories, considering the technical
        context from the epic analysis.

        Args:
            user_stories: List of previously generated user stories
            epic_analysis: Structured analysis of the epic's content
            task_tracker: Service for tracking generated tasks

        Returns:
            List of generated TechnicalTask objects

        Raises:
            Exception: If task generation fails or state cannot be saved
        """
        technical_tasks = await self.technical_task_generator.generate_technical_tasks(
            user_stories,
            epic_analysis.model_dump(),
            task_tracker,
            self.proposed_tickets
        )

        self._save_state("technical_tasks.json", [task.model_dump() for task in technical_tasks])
        return technical_tasks

    async def generate_subtasks(
            self,
            high_level_tasks: List[Union[UserStory, TechnicalTask]],
            epic_details: JiraTicketDetails,
            task_tracker: TaskTracker,
            task_type: str
    ) -> List[SubTask]:
        """
        Break down high-level tasks into detailed subtasks.

        This method generates specific, actionable subtasks for each high-level task,
        whether they are user stories or technical tasks. The subtasks include
        implementation details, acceptance criteria, and effort estimates.

        Args:
            high_level_tasks: List of user stories or technical tasks to break down
            epic_details: The parent epic's details from JIRA
            task_tracker: Service for tracking generated tasks
            task_type: Type of tasks being broken down ("user_story" or "technical_task")

        Returns:
            List of generated SubTask objects

        Raises:
            Exception: If subtask generation fails or state cannot be saved
        """
        subtasks = await self.subtask_generator.break_down_tasks(
            high_level_tasks,
            epic_details.model_dump(),
            task_tracker,
            self.proposed_tickets
        )

        self._save_state(f"{task_type}_subtasks.json", [subtask.model_dump() for subtask in subtasks])
        return subtasks

    async def generate_subtasks_parallel(
            self,
            high_level_tasks: List[Union[UserStory, TechnicalTask]],
            epic_details: JiraTicketDetails,
            task_tracker: TaskTracker,
            task_type: str,
            max_parallel: int = None
    ) -> List[SubTask]:
        """
        Break down high-level tasks into detailed subtasks in parallel.
        
        This method processes multiple high-level tasks concurrently to speed up
        the breakdown process.

        Args:
            high_level_tasks: List of user stories or technical tasks to break down
            epic_details: The parent epic's details from JIRA
            task_tracker: Service for tracking generated tasks
            task_type: Type of tasks being broken down ("user_story" or "technical_task")
            max_parallel: Maximum number of tasks to process in parallel (defaults to CPU count)

        Returns:
            List of generated SubTask objects

        Raises:
            Exception: If subtask generation fails or state cannot be saved
        """
        if not high_level_tasks:
            return []
            
        # Determine the number of workers based on CPU count and task size
        if max_parallel is None:
            max_parallel = min(multiprocessing.cpu_count(), len(high_level_tasks))
        max_parallel = max(1, min(max_parallel, len(high_level_tasks)))
        
        logger.info(f"Breaking down {len(high_level_tasks)} {task_type}s with {max_parallel} parallel workers")
        
        # Prepare the epic details once
        epic_details_dict = epic_details.model_dump()
        
        # Process tasks in chunks
        all_subtasks = []
        
        # We'll use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def process_task(task):
            async with semaphore:
                try:
                    logger.info(f"Processing task in parallel: {task.title}")
                    # For each task, create a list of one task
                    task_list = [task]
                    # Use the existing break_down_tasks method
                    task_subtasks = await self.subtask_generator.break_down_tasks(
                        task_list,
                        epic_details_dict,
                        task_tracker,
                        self.proposed_tickets
                    )
                    logger.info(f"Completed breakdown for {task.title} - generated {len(task_subtasks)} subtasks")
                    return task_subtasks
                except Exception as e:
                    logger.error(f"Error breaking down task {task.title}: {str(e)}")
                    # Don't fail all tasks if one fails
                    return []
        
        # Create tasks for all high-level tasks
        tasks = [process_task(task) for task in high_level_tasks]
        
        # Run all tasks and gather results
        results = await asyncio.gather(*tasks)
        
        # Flatten the results
        for subtask_list in results:
            all_subtasks.extend(subtask_list)
            
        # Save the combined results
        self._save_state(f"{task_type}_subtasks.json", [subtask.model_dump() for subtask in all_subtasks])
        return all_subtasks

    def _save_state(self, filename: str, data: Any) -> None:
        """
        Save execution state data to a JSON file.

        Args:
            filename: Name of the file to save (e.g., 'epic_details.json')
            data: Data to serialize and save

        Raises:
            IOError: If the file cannot be written
            Exception: If data cannot be serialized
        """
        filepath = self.state_dir / filename
        with open(filepath, 'w') as f:
            # Use custom JSON encoder for datetime objects
            json.dump(data, f, indent=2, default=lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
        logger.info(f"Saved state to {filepath}")

    def _load_state(self, filename: str) -> Any:
        """
        Load execution state data from a JSON file.

        Args:
            filename: Name of the file to load (e.g., 'epic_details.json')

        Returns:
            The deserialized data from the file

        Raises:
            FileNotFoundError: If the state file doesn't exist
            Exception: If the file cannot be read or parsed
        """
        filepath = self.state_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"State file {filepath} not found")
        with open(filepath, 'r') as f:
            return json.load(f)

    @classmethod
    def load_execution_state(
            cls,
            epic_key: str,
            execution_id: str,
            state_file: str
    ) -> Any:
        """
        Load a specific execution state from disk.

        Args:
            epic_key: The JIRA key of the epic
            execution_id: The execution ID
            state_file: The name of the state file to load

        Returns:
            The deserialized data from the file

        Raises:
            FileNotFoundError: If the state file doesn't exist
            Exception: If the file cannot be read or parsed
        """
        state_path = Path(f"execution_states/{epic_key}/{execution_id}/{state_file}")
        if not state_path.exists():
            raise FileNotFoundError(f"State file {state_path} not found")
        with open(state_path, 'r') as f:
            return json.load(f)

    async def execute_breakdown(self, config: Settings = None) -> EpicBreakdownResponse:
        """
        Execute the complete epic breakdown process.

        This is the main method that orchestrates the entire breakdown workflow:
        1. Analyzes the epic and retrieves details
        2. Generates user stories based on the analysis
        3. Creates technical tasks to support the user stories
        4. Breaks down both types of tasks into subtasks
        5. Tracks progress and maintains execution state
        6. Handles errors and saves execution results

        Args:
            config: Settings object with feature flag settings to override default settings
                   Keys should include: ENABLE_CODE_BLOCK_GENERATION, ENABLE_GHERKIN_SCENARIOS,
                   ENABLE_RESEARCH_TASKS, ENABLE_IMPLEMENTATION_APPROACH, ENABLE_TEST_PLANS

        Returns:
            EpicBreakdownResponse containing the complete breakdown results

        Raises:
            ValueError: If the epic cannot be found or analyzed
            Exception: For any other errors during execution
        """
        task_tracker = TaskTracker(self.epic_key)

        try:
            logger.info(f"Starting breakdown for epic: {self.epic_key}")
            
            # Pass config to the generators if provided
            if config:
                self.user_story_generator.set_config(config)
                self.technical_task_generator.set_config(config)
                self.subtask_generator.set_config(config)

            # Use the metrics tracker as a context manager
            async with EpicBreakdownTracker(self.epic_key):
                # Get epic details and analysis
                epic_details, epic_analysis = await self.analyze_epic_details()

                try:
                    # Generate high-level tasks
                    all_tasks: List[Union[UserStory, TechnicalTask]] = []

                    # Generate user stories
                    user_stories = await self.generate_user_stories(epic_analysis, task_tracker)
                    all_tasks.extend(user_stories)

                    # Generate subtasks for user stories in parallel
                    user_story_subtasks = await self.generate_subtasks_parallel(
                        user_stories,
                        epic_details,
                        task_tracker,
                        "user_story"
                    )

                    # Generate technical tasks
                    technical_tasks = await self.generate_technical_tasks(
                        user_stories,
                        epic_analysis,
                        task_tracker
                    )
                    all_tasks.extend(technical_tasks)

                    # Generate subtasks for technical tasks in parallel
                    tech_task_subtasks = await self.generate_subtasks_parallel(
                        technical_tasks,
                        epic_details,
                        task_tracker,
                        "technical_task"
                    )

                    # Combine all subtasks
                    all_subtasks = user_story_subtasks + tech_task_subtasks

                    # Generate metrics and save breakdown info
                    metrics_info = self._generate_metrics(all_tasks, all_subtasks)
                    self._save_breakdown_info(epic_details, epic_analysis, all_tasks, all_subtasks, metrics_info)

                    # Record successful completion
                    log_completion_summary(
                        self.epic_key,
                        len(user_stories),
                        len(technical_tasks),
                        len(all_subtasks),
                        task_tracker.error_count
                    )

                    # Return response
                    return EpicBreakdownResponse(
                        execution_id=self.execution_id,
                        epic_key=self.epic_key,
                        epic_details=epic_details,
                        epic_analysis=epic_analysis,
                        user_stories=user_stories,
                        technical_tasks=technical_tasks,
                        subtasks=all_subtasks,
                        metrics=metrics_info
                    )

                except Exception as e:
                    # Handle non-fatal task generation errors
                    self._handle_task_generation_error(e, task_tracker, epic_analysis)
                    raise

        except Exception as e:
            # Handle fatal breakdown errors
            self._handle_fatal_error(e)
            raise

    async def test_subtask_generation(
            self,
            epic_key: str,
            execution_id: str,
            task_type: str = "user_story"
    ) -> List[SubTask]:
        """
        Test the subtask generation process using saved state.

        This method allows testing the subtask generation in isolation by using
        previously saved state files. Useful for debugging and validation.

        Args:
            epic_key: The JIRA key of the epic
            execution_id: ID of the execution to load state from
            task_type: Type of tasks to generate subtasks for ("user_story" or "technical_task")

        Returns:
            List of generated SubTask objects

        Raises:
            FileNotFoundError: If required state files are not found
            Exception: If subtask generation fails
        """
        try:
            # Load required states
            epic_details_data = self.load_execution_state(epic_key, execution_id, "epic_details.json")
            epic_details = JiraTicketDetails(**epic_details_data)

            tasks_file = f"{task_type}s.json" if task_type == "user_story" else "technical_tasks.json"
            tasks_data = self.load_execution_state(epic_key, execution_id, tasks_file)

            # Convert loaded data back to models
            high_level_tasks = [
                UserStory(**task) if task_type == "user_story" else TechnicalTask(**task)
                for task in tasks_data
            ]

            # Create new task tracker for testing
            task_tracker = TaskTracker(epic_key)

            # Generate and return subtasks
            return await self.generate_subtasks(
                high_level_tasks,
                epic_details,
                task_tracker,
                task_type
            )

        except Exception as e:
            logger.error(f"Error in test_subtask_generation: {str(e)}")
            raise

    def _handle_task_generation_error(
            self,
            error: Exception,
            task_tracker: TaskTracker,
            epic_analysis: AnalysisInfo
    ) -> None:
        """
        Handle errors that occur during task generation.

        This method logs error details, saves the error state, and ensures the
        task tracker's state is preserved for debugging.

        Args:
            error: The exception that occurred
            task_tracker: The task tracker with current state
            epic_analysis: Analysis of the epic being processed
        """
        error_summary = task_tracker.get_summary()
        error_summary["errors"] = [str(error)]
        self.execution_log.log_summary(error_summary)

        self._save_state("error_state.json", {
            "error": str(error),
            "task_tracker_summary": error_summary,
            "epic_analysis": epic_analysis.model_dump()
        })

    def _handle_fatal_error(self, error: Exception) -> None:
        """
        Handle fatal errors that prevent execution from continuing.

        This method logs the error and saves the fatal error state for
        post-mortem analysis.

        Args:
            error: The fatal exception that occurred
        """
        self.execution_log.log_section("Fatal Error", str(error))
        self._save_state("fatal_error.json", {"error": str(error)})

    def _generate_metrics(self, all_tasks: List[Union[UserStory, TechnicalTask]], all_subtasks: List[SubTask]) -> MetricsInfo:
        """Generate metrics information from tasks and subtasks"""
        return MetricsInfo(
            total_story_points=sum(subtask.story_points for subtask in all_subtasks),
            estimated_days=sum(subtask.story_points for subtask in all_subtasks) / 5,  # Assuming 5 points per day
            required_skills=list(set(
                skill
                for subtask in all_subtasks
                for skill in subtask.required_skills
            ))
        )
        
    def _save_breakdown_info(
        self, 
        epic_details: JiraTicketDetails, 
        epic_analysis: AnalysisInfo,
        all_tasks: List[Union[UserStory, TechnicalTask]], 
        all_subtasks: List[SubTask],
        metrics_info: MetricsInfo
    ) -> None:
        """Save breakdown information to state files and MongoDB"""
        # Save proposed tickets to file
        self.proposed_tickets.save()
        
        # Create breakdown response for saving
        response = EpicBreakdownResponse(
            execution_id=self.execution_id,
            epic_key=self.epic_key,
            epic_details=epic_details,
            epic_analysis=epic_analysis,
            user_stories=[task for task in all_tasks if isinstance(task, UserStory)],
            technical_tasks=[task for task in all_tasks if isinstance(task, TechnicalTask)],
            subtasks=all_subtasks,
            metrics=metrics_info
        )
        
        # Save to MongoDB
        try:
            logger.info(f"Saving breakdown for epic {self.epic_key} to MongoDB")
            mongo_service = MongoDBService()
            
            # The proposed tickets file path
            proposed_plan_path = self.proposed_tickets.filename
            
            # Persist the plan to MongoDB
            if os.path.exists(proposed_plan_path):
                proposal_ids = mongo_service.persist_proposed_tickets_from_yaml(proposed_plan_path)
                logger.info(f"Saved breakdown to MongoDB with {len(proposal_ids)} proposal IDs")
                
                # Track the importation
                mongo_service.track_breakdown_import(
                    epic_key=self.epic_key,
                    execution_id=self.execution_id,
                    file_path=proposed_plan_path,
                    proposal_ids=proposal_ids
                )
            else:
                logger.warning(f"Proposed tickets file not found at {proposed_plan_path}")
                
            # Save execution record
            asyncio.create_task(self.execution_log.create_execution_record(
                execution_id=self.execution_id,
                epic_key=self.epic_key,
                execution_plan_file=self.execution_log.filename,
                proposed_plan_file=self.proposed_tickets.filename,
                status="SUCCESS"
            ))
        except Exception as e:
            logger.error(f"Error saving breakdown to MongoDB: {str(e)}")
        
        # Save final state to file
        try:
            self._save_state("final_result.json", response.model_dump())
        except Exception as e:
            logger.error(f"Error saving final result: {str(e)}")
