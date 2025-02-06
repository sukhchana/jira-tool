from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from services.jira_service import JiraService
from services.prompt_helper_service import PromptHelperService
from services.ticket_parser_service import TicketParserService
from llm.vertexllm import VertexLLM
from loguru import logger
import json
from services.execution_log_service import ExecutionLogService
from services.task_tracker import TaskTracker
from services.validation_helper import ValidationHelper
from services.proposed_tickets_service import ProposedTicketsService
from services.execution_tracker_service import ExecutionTrackerService
from uuid_extensions import uuid7
from config.breakdown_config import BreakdownConfig
from datetime import datetime

class JiraBreakdownService:
    """
    Service responsible for orchestrating the breakdown of JIRA epics into smaller tasks.
    
    This service coordinates between different components:
    - VertexLLM for generating content
    - PromptHelper for managing LLM prompts
    - TicketParser for parsing LLM responses
    - JiraService for JIRA interactions
    
    Flow:
    1. Receives epic details from JIRA
    2. Analyzes epic scope using LLM
    3. Generates high-level tasks
    4. Breaks down tasks into detailed subtasks
    5. Optionally creates tickets in JIRA
    """

    def __init__(self):
        """Initialize all required services for epic breakdown"""
        logger.info("Initializing JiraBreakdownService")
        self.jira_service = JiraService()
        self.llm = VertexLLM()
        self.prompt_helper = PromptHelperService()
        self.parser = TicketParserService()
        self.execution_tracker = ExecutionTrackerService()
        logger.info("Successfully initialized all required services")

    async def generate_ticket_description(
        self,
        context: str,
        requirements: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate a structured JIRA ticket description using LLM.

        Flow:
        1. Build prompt using context and requirements
        2. Generate content using LLM
        3. Parse response into structured format

        Args:
            context: Main context/purpose of the ticket
            requirements: Optional specific requirements
            additional_info: Optional additional context or constraints

        Returns:
            Dict containing:
            - summary: Brief ticket title
            - description: Detailed explanation
            - acceptance_criteria: List of acceptance criteria
            - technical_notes: Technical considerations
        """
        prompt = self.prompt_helper.build_ticket_prompt(context, requirements, additional_info)
        response = await self.llm.generate_content(prompt)
        return self.parser.parse_ticket_description(response)

    async def analyze_ticket_complexity(self, ticket_description: str) -> Dict[str, Any]:
        """
        Analyze the complexity of a ticket and estimate effort.

        Flow:
        1. Build analysis prompt from ticket description
        2. Generate analysis using LLM
        3. Return complexity assessment

        Args:
            ticket_description: The description of the ticket to analyze

        Returns:
            Dict containing:
            - analysis: Structured complexity analysis
            - raw_response: Original LLM response
        """
        prompt = self.prompt_helper.build_complexity_prompt(ticket_description)
        response = await self.llm.generate_content(
            prompt,
            max_output_tokens=512,
            temperature=0.1
        )
        return {
            "analysis": response,
            "raw_response": response
        }

    async def break_down_epic(
        self,
        epic_key: str,
        config: Optional[BreakdownConfig] = None
    ) -> Dict[str, Any]:
        """Break down a JIRA epic into smaller tasks"""
        execution_id = str(uuid7())
        execution_log = ExecutionLogService(epic_key)
        task_tracker = TaskTracker(epic_key)
        proposed_tickets = ProposedTicketsService()
        
        try:
            logger.info("=== Creating Initial Execution Record ===")
            logger.info(f"execution_id: {execution_id}")
            logger.info(f"epic_key: {epic_key}")
            logger.info(f"execution_plan_file: {execution_log.filename}")
            logger.info(f"proposed_plan_file: ''")
            logger.info(f"status: NEW")
            
            # Create initial execution record
            await self.execution_tracker.create_execution_record(
                execution_id=execution_id,
                epic_key=epic_key,
                execution_plan_file=execution_log.filename,
                proposed_plan_file="",  # Will be updated later
                status="NEW"  # Initial status
            )
            
            # Use default config if none provided
            if config is None:
                config = BreakdownConfig()
                
            # Get epic details from JIRA
            epic = await self.jira_service.get_ticket(epic_key)
            
            # Build prompt with constraints
            prompt = f"""
            Please break down the following JIRA epic into smaller tasks.
            
            Epic Title: {epic["summary"]}
            Epic Description: {epic["description"]}
            
            {config.to_prompt_constraints()}
            
            Please provide a structured breakdown including:
            ...
            """
            
            logger.info(f"Breaking down epic: {epic_key}")
            
            # Analyze epic
            response = await self.llm.generate_content(prompt)
            epic_analysis = self.parser.parse_epic_analysis(response)
            
            execution_log.log_llm_interaction(
                "Epic Analysis",
                prompt,
                response,
                epic_analysis
            )
            
            try:
                await self._generate_high_level_tasks(
                    epic_analysis,
                    execution_log,
                    task_tracker,
                    proposed_tickets,
                    execution_id,
                    epic_key
                )
                
                await self._break_down_tasks(
                    task_tracker.get_all_tasks(),
                    epic,
                    execution_log,
                    task_tracker,
                    proposed_tickets,
                    config
                )
                
                # Get final tasks after breakdown
                final_tasks = task_tracker.get_all_tasks()
                
                # Store final proposal and update execution record
                proposal_id = await proposed_tickets.store_proposal(
                    execution_id=execution_id,
                    epic_key=epic_key,
                    high_level_tasks=final_tasks
                )
                
                # Export to YAML
                yaml_file = await proposed_tickets.export_proposal_to_yaml(proposal_id)
                
                # Update execution record with success status and yaml file
                await self.execution_tracker.update_execution_status(
                    execution_id=execution_id,
                    status="COMPLETED"
                )
                
                # Use task tracker for summary
                summary = task_tracker.get_summary()
                execution_log.log_summary(summary)
                
                return {
                    "execution_id": execution_id,
                    "epic_key": epic_key,
                    "epic_summary": epic["summary"],
                    "analysis": epic_analysis,
                    "tasks": final_tasks,
                    "execution_plan_file": execution_log.filename,
                    "proposed_tickets_file": yaml_file,
                    "proposal_id": proposal_id
                }
                
            except Exception as e:
                # Update execution record with failed status
                await self.execution_tracker.update_execution_status(
                    execution_id=execution_id,
                    status="FAILED"
                )
                
                # Use task tracker for error summary
                error_summary = task_tracker.get_summary()
                error_summary["errors"] = [str(e)]
                execution_log.log_summary(error_summary)
                
                logger.error(f"Failed during task generation: {str(e)}")
                logger.error("Tasks structure at time of error:")
                logger.error(json.dumps(task_tracker.get_all_tasks() if 'tasks' in locals() else "No tasks generated", indent=2))
                logger.error(f"Epic analysis that caused error:\n{epic_analysis}")
                return {
                    "epic_key": epic_key,
                    "epic_summary": epic["summary"],
                    "analysis": epic_analysis,
                    "error": str(e),
                    "tasks": [],
                    "execution_id": execution_id,
                    "status": "FAILED",
                    "proposal_id": proposal_id
                }
                
        except Exception as e:
            # Update execution record with fatal error status if it was created
            try:
                await self.execution_tracker.update_execution_status(
                    execution_id=execution_id,
                    status="FATAL_ERROR"
                )
            except ValueError:
                # Record might not exist yet, log and continue
                logger.warning(f"Could not update status for execution {execution_id}")
            
            # Fatal error during setup or epic retrieval
            execution_log.log_section("Fatal Error", str(e))
            
            logger.error(f"Fatal error breaking down epic: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to break down epic: {str(e)}"
            )

    async def _analyze_epic_scope(self, summary: str, description: str) -> Dict[str, Any]:
        """Analyze the scope and requirements of an epic."""
        try:
            prompt = self.prompt_helper.build_epic_analysis_prompt(summary, description)
            logger.debug(f"Epic analysis prompt:\n{prompt}")
            
            response = await self.llm.generate_content(prompt)
            logger.info("Raw LLM response for epic analysis:")
            logger.info("-" * 80)
            logger.info(response)
            logger.info("-" * 80)
            
            parsed = self.parser.parse_epic_analysis(response)
            logger.debug(f"Parsed epic analysis:\n{json.dumps(parsed, indent=2)}")
            return parsed
        except Exception as e:
            logger.error(f"Failed to analyze epic scope: {str(e)}")
            logger.error(f"Summary: {summary}")
            logger.error(f"Description: {description}")
            raise

    async def _generate_high_level_tasks(
        self,
        epic_analysis: Dict[str, Any],
        execution_log: ExecutionLogService,
        task_tracker: TaskTracker,
        proposed_tickets: ProposedTicketsService,
        execution_id: str,
        epic_key: str
    ):
        """Generate high-level tasks based on epic analysis"""
        try:
            # Generate user stories first
            prompt = self.prompt_helper.build_user_stories_prompt(epic_analysis)
            response = await self.llm.generate_content(prompt)
            user_stories = self.parser.parse_user_stories(response)
            
            # Add tasks to tracker and get IDs
            for story in user_stories:
                task_tracker.add_user_story(story)
                story["id"] = proposed_tickets.add_high_level_task(
                    task=story,
                    epic_key=epic_key,
                    proposal_id=execution_id,
                    execution_id=execution_id
                )
            
            # Generate technical tasks
            prompt = self.prompt_helper.build_technical_tasks_prompt(user_stories, epic_analysis)
            response = await self.llm.generate_content(prompt)
            technical_tasks = self.parser.parse_technical_tasks(response)
            
            # Add tasks to tracker and get IDs
            for task in technical_tasks:
                task_id = proposed_tickets.add_high_level_task(
                    task=task,
                    epic_key=epic_key,
                    proposal_id=execution_id,
                    execution_id=execution_id
                )
                task["id"] = task_id  # Store the ID in the task dict instead
                task_tracker.add_technical_task(task)  # Only pass the task
            
            # Verify task tracker state
            tracker_state = task_tracker.get_summary()
            logger.debug("Task Tracker State:")
            logger.debug(f"- User Stories: {len(task_tracker.user_stories)}")
            logger.debug(f"- Technical Tasks: {len(task_tracker.technical_tasks)}")
            logger.debug(f"Full state: {json.dumps(tracker_state, indent=2)}")
            
            # Verify the structure of get_all_tasks
            all_tasks = task_tracker.get_all_tasks()
            logger.debug("\nTask Structure Check:")
            logger.debug(f"Total tasks: {len(all_tasks)}")
            for task in all_tasks:
                logger.debug(f"Task type: {task['high_level_task']['type']}")
                logger.debug(f"Task name: {task['high_level_task']['name']}")
            
            # Log interactions with more detail
            execution_log.log_llm_interaction(
                "User Stories Generation",
                prompt,
                response,
                {
                    "generated_stories": len(user_stories),
                    "stories": user_stories
                }
            )
            execution_log.log_llm_interaction(
                "Technical Tasks Generation",
                prompt,
                response,
                {
                    "generated_tasks": len(technical_tasks),
                    "tasks": technical_tasks
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to generate high-level tasks: {str(e)}")
            logger.error(f"Epic analysis: {json.dumps(epic_analysis, indent=2)}")
            if 'technical_tasks' in locals():
                logger.error(f"Technical tasks at time of error: {json.dumps(technical_tasks, indent=2)}")
            raise

    async def _break_down_tasks(
        self,
        tasks: List[Dict[str, Any]],
        epic_details: Dict[str, Any],
        execution_log: ExecutionLogService,
        task_tracker: TaskTracker,
        proposed_tickets: ProposedTicketsService,
        config: Optional[BreakdownConfig] = None
    ) -> None:
        """Break down high-level tasks into subtasks"""
        if config is None:
            config = BreakdownConfig()

        for task in tasks:
            prompt = self.prompt_helper.build_task_breakdown_prompt(
                task_type=task["type"],
                task_summary=task["summary"],
                epic_context=epic_details,
                config=config
            )

            response = await self.llm.generate_content(prompt)
            subtasks = self.parser.parse_subtasks(response)

            # Rest of the method...

    async def create_epic_subtasks(
        self,
        epic_key: str,
        breakdown: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create JIRA tickets for all subtasks in the epic breakdown.

        Flow:
        1. Validate the breakdown structure
        2. Create tickets for each subtask
        3. Link subtasks to the parent epic
        4. Set additional fields (story points, labels, etc.)

        Args:
            epic_key: The parent epic's key
            breakdown: The epic breakdown structure

        Returns:
            List of created JIRA tickets

        Raises:
            HTTPException: If ticket creation fails
        """
        try:
            logger.info(f"Creating JIRA tickets for epic {epic_key}")
            created_tasks = []
            project_key = epic_key.split("-")[0]

            for task_group in breakdown["tasks"]:
                # Create a story for the high-level task
                high_level_task = task_group["high_level_task"]
                story = await self.jira_service.create_ticket({
                    "project_key": project_key,
                    "summary": high_level_task["name"],
                    "description": (
                        f"{high_level_task['description']}\n\n"
                        f"Technical Domain: {high_level_task['technical_domain']}\n"
                        f"Complexity: {high_level_task['complexity']}\n"
                        f"Dependencies: {', '.join(high_level_task['dependencies'])}"
                    ),
                    "issue_type": "Story",
                    "parent_key": epic_key  # Link to parent epic
                })
                created_tasks.append(story)

                # Create subtasks
                for subtask in task_group["subtasks"]:
                    task = await self.jira_service.create_ticket({
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