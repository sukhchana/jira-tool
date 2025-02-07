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
from uuid_extensions import uuid7
from models.responses import EpicBreakdownResponse
from models.task_group import TaskGroup
from models.sub_task import SubTask
from models.proposed_tickets import ProposedTickets
import yaml

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

    def __init__(self, epic_key: str):
        """Initialize the breakdown service with dependencies"""
        self.epic_key = epic_key
        self.execution_id = str(uuid7())  # Generate execution ID at initialization
        self.execution_log = ExecutionLogService(epic_key)
        self.proposed_tickets = ProposedTicketsService(epic_key=epic_key, execution_id=self.execution_id)
        self.prompt_helper = PromptHelperService()
        self.jira = JiraService()
        logger.info("Initializing JiraBreakdownService")
        self.llm = VertexLLM()
        self.parser = TicketParserService()
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

    async def break_down_epic(self) -> Dict[str, Any]:
        """Break down a JIRA epic into smaller tasks"""
        execution_id = str(uuid7())
        task_tracker = TaskTracker(self.epic_key)
        
        try:
            logger.info(f"Breaking down epic: {self.epic_key}")
            
            # Get epic details
            epic_details = await self.jira.get_ticket(self.epic_key)
            self.execution_log.log_section("Epic Details", json.dumps(epic_details, indent=2))
            
            # Analyze epic
            prompt = self.prompt_helper.build_epic_analysis_prompt(
                epic_details["summary"],
                epic_details["description"]
            )
            response = await self.llm.generate_content_with_search(
                prompt,
                temperature=0.2
            )
            epic_analysis = self.parser.parse_epic_analysis(response)
            
            self.execution_log.log_llm_interaction(
                "Epic Analysis",
                prompt,
                response,
                epic_analysis
            )
            
            try:
                # Pass both execution_log and task_tracker
                await self._generate_high_level_tasks(
                    epic_analysis,
                    task_tracker,
                    self.proposed_tickets
                )
                
                # Debug log task tracker state before breakdown
                logger.debug("Task tracker state before breakdown:")
                logger.debug(task_tracker.debug_state())
                
                all_tasks = task_tracker.get_all_tasks()
                logger.debug(f"Tasks from tracker:\n{json.dumps(all_tasks, indent=2)}")
                
                await self._break_down_tasks(
                    all_tasks,
                    epic_details,
                    self.execution_log,
                    task_tracker,
                    self.proposed_tickets
                )
                
                # Save the proposed tickets
                self.proposed_tickets.save()
                
                # Use task tracker for summary
                summary = task_tracker.get_summary()
                self.execution_log.log_summary(summary)
                
                # Save successful execution record
                await self.execution_log.create_execution_record(
                    execution_id=execution_id,
                    epic_key=self.epic_key,
                    execution_plan_file=self.execution_log.filename,
                    proposed_plan_file=self.proposed_tickets.filename,
                    status="SUCCESS"
                )
                
                return {
                    "execution_id": execution_id,
                    "epic_key": self.epic_key,
                    "epic_summary": epic_details["summary"],
                    "analysis": epic_analysis,
                    "tasks": task_tracker.get_all_tasks(),
                    "execution_plan_file": self.execution_log.filename,
                    "proposed_tickets_file": self.proposed_tickets.filename
                }
                
            except Exception as e:
                # Use task tracker for error summary
                error_summary = task_tracker.get_summary()
                error_summary["errors"] = [str(e)]
                self.execution_log.log_summary(error_summary)
                
                # Save failed execution record
                await self.execution_log.create_execution_record(
                    execution_id=execution_id,
                    epic_key=self.epic_key,
                    execution_plan_file=self.execution_log.filename,
                    proposed_plan_file=self.proposed_tickets.filename,
                    status="FAILED"
                )
                
                logger.error(f"Failed during task generation: {str(e)}")
                logger.error("Tasks structure at time of error:")
                logger.error(json.dumps(task_tracker.get_all_tasks() if 'tasks' in locals() else "No tasks generated", indent=2))
                logger.error(f"Epic analysis that caused error:\n{epic_analysis}")
                return {
                    "epic_key": self.epic_key,
                    "epic_summary": epic_details["summary"],
                    "analysis": epic_analysis,
                    "error": str(e),
                    "tasks": [],
                    "execution_id": execution_id,  # Add execution_id to error response
                    "status": "FAILED"
                }
                
        except Exception as e:
            # Fatal error during setup or epic retrieval
            self.execution_log.log_section("Fatal Error", str(e))
            
            # Save fatal error execution record
            await self.execution_log.create_execution_record(
                execution_id=execution_id,
                epic_key=self.epic_key,
                execution_plan_file=self.execution_log.filename,
                proposed_plan_file="",  # No proposed tickets in fatal error
                status="FATAL_ERROR"
            )
            
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
        task_tracker: TaskTracker,
        proposed_tickets: ProposedTicketsService
    ) -> None:
        """Generate high-level tasks based on epic analysis"""
        try:
            # Generate user stories first
            prompt = self.prompt_helper.build_user_stories_prompt(epic_analysis)
            response = await self.llm.generate_content_with_search(
                prompt,
                temperature=0.2
            )
            user_stories = self.parser.parse_user_stories(response)
            
            # Add tasks to tracker and get IDs
            task_name_to_id = {}  # Map to store task names to IDs
            
            # Process user stories
            for story in user_stories:
                task_tracker.add_user_story(story)
                story["id"] = proposed_tickets.add_high_level_task(story)
                task_name_to_id[story["name"]] = story["id"]
            
            # Generate technical tasks
            prompt = self.prompt_helper.build_technical_tasks_prompt(user_stories, epic_analysis)
            response = await self.llm.generate_content_with_search(
                prompt,
                temperature=0.2
            )
            technical_tasks = self.parser.parse_technical_tasks(response)
            
            # Process technical tasks
            for task in technical_tasks:
                task_tracker.add_technical_task(task)
                task["id"] = proposed_tickets.add_high_level_task(task)
                task_name_to_id[task["name"]] = task["id"]
            
            # Resolve dependencies using the name-to-id mapping
            self._resolve_task_dependencies(user_stories + technical_tasks, task_name_to_id)
            
            # Update tasks in tracker and proposed tickets with resolved dependencies
            for task in user_stories + technical_tasks:
                task_tracker.update_task_dependencies(task["name"], task["dependencies"])
                proposed_tickets.update_task_dependencies(task["id"], task["dependencies"])
            
            # Verify task tracker state
            tracker_state = task_tracker.get_summary()
            logger.debug("Task Tracker State:")
            logger.debug(f"- User Stories: {len(task_tracker.user_stories)}")
            logger.debug(f"- Technical Tasks: {len(task_tracker.technical_tasks)}")
            logger.debug(f"Full state: {json.dumps(tracker_state, indent=2)}")
            
            # Log interactions with more detail
            self.execution_log.log_llm_interaction(
                "User Stories Generation",
                prompt,
                response,
                {
                    "generated_stories": len(user_stories),
                    "stories": user_stories
                }
            )
            self.execution_log.log_llm_interaction(
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

    def _resolve_task_dependencies(self, tasks: List[Dict[str, Any]], task_name_to_id: Dict[str, str]) -> None:
        """
        Resolve task dependencies from names to IDs.
        
        Args:
            tasks: List of tasks with dependencies
            task_name_to_id: Mapping of task names to their IDs
        """
        for task in tasks:
            resolved_dependencies = []
            for dep in task["dependencies"]:
                # Clean up the dependency name and try to find its ID
                dep_name = dep.strip()
                if dep_name.lower() == "none":
                    continue
                    
                # Try to find the ID for this dependency
                if dep_name in task_name_to_id:
                    resolved_dependencies.append(task_name_to_id[dep_name])
                else:
                    # If we can't find the exact name, try to find a partial match
                    matches = [name for name in task_name_to_id.keys() if dep_name in name]
                    if matches:
                        resolved_dependencies.append(task_name_to_id[matches[0]])
                    else:
                        logger.warning(f"Could not resolve dependency '{dep_name}' for task '{task['name']}'")
            
            # Update the task's dependencies with resolved IDs
            task["dependencies"] = resolved_dependencies

    async def _break_down_tasks(
        self,
        high_level_tasks: List[Dict[str, Any]],
        epic_details: Dict[str, Any],
        execution_log: ExecutionLogService,
        task_tracker: TaskTracker,
        proposed_tickets: ProposedTicketsService
    ) -> None:
        """Break down high-level tasks into detailed subtasks."""
        try:
            # Debug log the input tasks
            logger.debug(f"Received high-level tasks for breakdown:\n{json.dumps(high_level_tasks, indent=2)}")
            
            # Process each task
            for task_group in high_level_tasks:
                try:
                    task = task_group["high_level_task"]
                    logger.info(f"Breaking down task: {task['name']} ({task['type']})")
                    
                    prompt = self.prompt_helper.build_subtasks_prompt(task, epic_details)
                    response = await self.llm.generate_content(prompt)
                    
                    # Log the subtask generation attempt
                    logger.info(f"Raw LLM response for subtasks of {task['name']}:")
                    logger.info("-" * 80)
                    logger.info(response)
                    logger.info("-" * 80)
                    
                    subtasks = self.parser.parse_subtasks(response)
                    
                    # Log parsed subtasks
                    logger.info(f"Parsed {len(subtasks)} subtasks for {task['name']}:")
                    for subtask in subtasks:
                        logger.info(f"- {subtask['title']} ({subtask['story_points']} points)")
                        logger.debug(f"  Details: {json.dumps(subtask, indent=2)}")
                    
                    # Add to execution log
                    execution_log.log_section(
                        f"Subtasks for {task['name']}", 
                        json.dumps({
                            "parent_task": task['name'],
                            "parent_type": task['type'],
                            "subtask_count": len(subtasks),
                            "total_points": sum(st['story_points'] for st in subtasks),
                            "subtasks": subtasks
                        }, indent=2)
                    )
                    
                    task_tracker.add_subtasks(task["name"], subtasks)
                    proposed_tickets.add_subtasks(
                        parent_name=task["name"],
                        subtasks=subtasks,
                        parent_id=task["id"]  # Access ID directly from task
                    )
                    logger.info(f"Completed breakdown for {task['name']} - {len(subtasks)} subtasks created")
                    
                except Exception as e:
                    logger.error(f"Failed to break down task {task['name']}: {str(e)}")
                    logger.error(f"Task details: {json.dumps(task, indent=2)}")
                    raise

            # Get final summary including subtasks
            tracker_summary = task_tracker.get_summary()
            total_tasks = len(high_level_tasks)
            total_subtasks = tracker_summary['subtasks']
            
            # Calculate additional statistics
            avg_story_points = 0
            total_story_points = 0
            skills_required = set()
            max_subtasks = 0
            min_subtasks = float('inf') if total_tasks > 0 else 0

            for parent, subtasks in task_tracker.subtasks.items():
                subtask_count = len(subtasks)
                max_subtasks = max(max_subtasks, subtask_count)
                min_subtasks = min(min_subtasks, subtask_count)
                
                for subtask in subtasks:
                    total_story_points += subtask.get('story_points', 0)
                    skills_required.update(subtask.get('required_skills', []))

            avg_story_points = total_story_points / total_subtasks if total_subtasks > 0 else 0

            # Calculate the average outside the f-string
            avg_subtasks = (total_subtasks/total_tasks if total_tasks > 0 else 0)
            avg_points = (total_story_points/total_subtasks if total_subtasks > 0 else 0)
            estimated_days = (total_story_points/5 if total_story_points > 0 else 0)

            completion_summary = (
                f"\nTask Breakdown Completion Report\n"
                f"===============================\n\n"
                f"High-Level Tasks:\n"
                f"- Total tasks processed: {total_tasks}\n"
                f"- User Stories: {tracker_summary['user_stories']}\n"
                f"- Technical Tasks: {tracker_summary['technical_tasks']}\n\n"
                
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

            # Add detailed breakdown by parent task
            for parent, count in tracker_summary['subtasks_by_parent'].items():
                parent_subtasks = task_tracker.subtasks.get(parent, [])
                parent_points = sum(subtask.get('story_points', 0) for subtask in parent_subtasks)
                completion_summary += (
                    f"- {parent}:\n"
                    f"  • Subtasks: {count}\n"
                    f"  • Story Points: {parent_points}\n"
                    f"  • Required Skills: {', '.join(sorted(set(skill for subtask in parent_subtasks for skill in subtask.get('required_skills', []))))}\n"
                )

            # Add detailed subtask information to execution log
            execution_log.log_section(
                "Final Subtask Summary",
                json.dumps({
                    "total_high_level_tasks": total_tasks,
                    "total_subtasks": total_subtasks,
                    "subtasks_by_parent": tracker_summary['subtasks_by_parent'],
                    "all_subtasks": task_tracker.subtasks
                }, indent=2)
            )

            logger.info(completion_summary)
            execution_log.log_section("Task Breakdown Completion", completion_summary)

        except Exception as e:
            logger.error(f"Failed to break down tasks: {str(e)}")
            logger.error(f"High-level tasks: {json.dumps(high_level_tasks, indent=2)}")
            logger.error(f"Epic details: {json.dumps(epic_details, indent=2)}")
            raise

    async def create_epic_subtasks(
        self,
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
            breakdown: The epic breakdown structure

        Returns:
            List of created JIRA tickets

        Raises:
            HTTPException: If ticket creation fails
        """
        try:
            logger.info(f"Creating JIRA tickets for epic {self.epic_key}")
            created_tasks = []
            project_key = self.epic_key.split("-")[0]

            for task_group in breakdown["tasks"]:
                # Create a story for the high-level task
                high_level_task = task_group["high_level_task"]
                story = await self.jira.create_ticket({
                    "project_key": project_key,
                    "summary": high_level_task["name"],
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
                    task = await self.jira.create_ticket({
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