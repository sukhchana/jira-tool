from typing import Dict, Any, List, Union
from loguru import logger
from prompts.subtask_prompt_builder import SubtaskPromptBuilder
from services.task_tracker import TaskTracker
from services.proposed_tickets_service import ProposedTicketsService
from services.execution_log_service import ExecutionLogService
from llm.vertexllm import VertexLLM
from models.user_story import UserStory
from models.technical_task import TechnicalTask
from models.sub_task import SubTask
from parsers import SubtaskParser
from .breakdown_summary_logger import log_completion_summary
import json

class SubtaskGenerator:
    """Service responsible for breaking down high-level tasks into subtasks"""
    
    def __init__(self, execution_log: ExecutionLogService):
        self.llm = VertexLLM()
        self.execution_log = execution_log
    
    async def break_down_tasks(
        self,
        high_level_tasks: List[Union[UserStory, TechnicalTask]],
        epic_details: Dict[str, Any],
        task_tracker: TaskTracker,
        proposed_tickets: ProposedTicketsService
    ) -> List[SubTask]:
        """
        Break down User Stories and Technical Tasks into detailed subtasks.
        
        Args:
            high_level_tasks: List of UserStory or TechnicalTask objects to break down
            epic_details: Details of the parent epic
            task_tracker: TaskTracker instance
            proposed_tickets: ProposedTicketsService instance
            
        Returns:
            List of SubTask objects
        """
        all_subtasks: List[SubTask] = []
        
        try:
            # Process each task
            for task in high_level_tasks:
                try:
                    task_dict = task.dict()
                    logger.info(f"Breaking down task: {task.title} ({task.type})")
                    
                    # Generate subtasks
                    subtasks = await self._generate_subtasks(task_dict, epic_details)
                    
                    # Add to all subtasks list
                    all_subtasks.extend(subtasks)
                    
                    # Log the breakdown
                    self.execution_log.log_section(
                        f"Subtasks for {task.title}", 
                        json.dumps({
                            "parent_task": task.title,
                            "parent_type": task.type,
                            "subtask_count": len(subtasks),
                            "total_points": sum(st.story_points for st in subtasks),
                            "subtasks": [st.dict() for st in subtasks]
                        }, indent=2)
                    )
                    
                    # Add subtasks to tracking systems
                    task_tracker.add_subtasks(task.title, [st.dict() for st in subtasks])
                    proposed_tickets.add_subtasks(
                        parent_name=task.title,
                        subtasks=[st.dict() for st in subtasks],
                        parent_id=task.id
                    )
                    
                    logger.info(f"Completed breakdown for {task.title} - {len(subtasks)} subtasks created")
                    
                except Exception as e:
                    error_msg = f"Failed to break down task {task.title}"
                    logger.error(f"{error_msg}: {str(e)}")
                    logger.error(f"Task details: {json.dumps(task.dict(), indent=2)}")
                    raise
            
            return all_subtasks
            
        except Exception as e:
            logger.error(f"Failed to break down tasks: {str(e)}")
            logger.error(f"High-level tasks: {json.dumps([t.dict() for t in high_level_tasks], indent=2)}")
            raise
    
    async def _generate_subtasks(
        self,
        parent_task: Dict[str, Any],
        epic_details: Dict[str, Any]
    ) -> List[SubTask]:
        """
        Generate subtasks for a high-level task.
        
        Args:
            parent_task: The high-level task to break down
            epic_details: Details of the parent epic
            
        Returns:
            List of generated subtasks
        """
        try:
            # Build and execute subtask generation prompt
            prompt = SubtaskPromptBuilder.build_subtasks_prompt(parent_task, epic_details)
            response = await self.llm.generate_content(prompt)
            
            # Log the interaction
            logger.info(f"Raw LLM response for subtasks of {parent_task['title']}:")
            logger.info("-" * 80)
            logger.info(response)
            logger.info("-" * 80)
            
            # Parse subtasks
            subtasks = SubtaskParser.parse(response)
            
            # Log parsed results
            logger.info(f"Parsed {len(subtasks)} subtasks for {parent_task['title']}:")
            for subtask in subtasks:
                logger.info(f"- {subtask.title} ({subtask.story_points} points)")
                logger.debug(f"  Details: {json.dumps(subtask.dict(), indent=2)}")
            
            return subtasks
            
        except Exception as e:
            logger.error(f"Failed to generate subtasks: {str(e)}")
            logger.error(f"Parent task: {json.dumps(parent_task, indent=2)}")
            raise 