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

    async def break_down_epic(self, epic_key: str) -> Dict[str, Any]:
        """Break down a JIRA epic into smaller tasks"""
        execution_log = ExecutionLogService(epic_key)
        task_tracker = TaskTracker(epic_key)
        proposed_tickets = ProposedTicketsService(epic_key, execution_log.execution_id)
        
        try:
            logger.info(f"Breaking down epic: {epic_key}")
            
            # Get epic details
            epic_details = await self.jira_service.get_ticket(epic_key)
            execution_log.log_section("Epic Details", json.dumps(epic_details, indent=2))
            
            # Analyze epic
            prompt = self.prompt_helper.build_epic_analysis_prompt(
                epic_details["summary"],
                epic_details["description"]
            )
            response = await self.llm.generate_content(prompt)
            epic_analysis = self.parser.parse_epic_analysis(response)
            
            execution_log.log_llm_interaction(
                "Epic Analysis",
                prompt,
                response,
                epic_analysis
            )
            
            try:
                # Pass both execution_log and task_tracker
                await self._generate_high_level_tasks(
                    epic_analysis,
                    execution_log,
                    task_tracker,
                    proposed_tickets
                )
                
                # Debug log task tracker state before breakdown
                logger.debug("Task tracker state before breakdown:")
                logger.debug(task_tracker.debug_state())
                
                all_tasks = task_tracker.get_all_tasks()
                logger.debug(f"Tasks from tracker:\n{json.dumps(all_tasks, indent=2)}")
                
                await self._break_down_tasks(
                    all_tasks,
                    epic_details,
                    execution_log,
                    task_tracker,
                    proposed_tickets
                )
                
                # Save the proposed tickets
                proposed_tickets.save()
                
                # Use task tracker for summary
                summary = task_tracker.get_summary()
                execution_log.log_summary(summary)
                
                return {
                    "epic_key": epic_key,
                    "epic_summary": epic_details["summary"],
                    "analysis": epic_analysis,
                    "tasks": task_tracker.get_all_tasks(),
                    "proposed_tickets_file": proposed_tickets.filename
                }
                
            except Exception as e:
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
                    "epic_summary": epic_details["summary"],
                    "analysis": epic_analysis,
                    "error": str(e),
                    "tasks": []
                }
                
        except Exception as e:
            execution_log.log_section("Fatal Error", str(e))
            logger.error(f"Failed to break down epic: {str(e)}")
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
        proposed_tickets: ProposedTicketsService
    ) -> None:
        """Generate high-level tasks based on epic analysis"""
        try:
            # Generate User Stories
            stories_prompt = self.prompt_helper.build_user_stories_prompt(epic_analysis)
            stories_response = await self.llm.generate_content(stories_prompt, temperature=0.7)
            user_stories = self.parser.parse_user_stories(stories_response)
            logger.debug(f"Generated {len(user_stories)} user stories")
            
            # Debug log each user story
            for story in user_stories:
                logger.debug(f"User Story: {json.dumps(story, indent=2)}")
                task_tracker.add_user_story(story)
                proposed_tickets.add_high_level_task(story)
            
            # Generate Technical Tasks
            tasks_prompt = self.prompt_helper.build_technical_tasks_prompt(user_stories, epic_analysis)
            tasks_response = await self.llm.generate_content(tasks_prompt, temperature=0.7)
            technical_tasks = self.parser.parse_technical_tasks(tasks_response)
            logger.debug(f"Generated {len(technical_tasks)} technical tasks")
            
            # Debug log each technical task
            for task in technical_tasks:
                logger.debug(f"Technical Task: {json.dumps(task, indent=2)}")
                task_tracker.add_technical_task(task)
                proposed_tickets.add_high_level_task(task)
            
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
                stories_prompt,
                stories_response,
                {
                    "generated_stories": len(user_stories),
                    "stories": user_stories
                }
            )
            execution_log.log_llm_interaction(
                "Technical Tasks Generation",
                tasks_prompt,
                tasks_response,
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
            
            # Check if we have any tasks to process
            if not high_level_tasks:
                logger.warning("No high-level tasks to break down")
                logger.debug(f"Current task tracker state:\n{json.dumps(task_tracker.get_summary(), indent=2)}")
                completion_summary = (
                    f"\nTask breakdown completed:\n"
                    f"- Total high-level tasks processed: 0\n"
                    f"- Total subtasks created: 0\n"
                    f"- Average subtasks per task: 0\n"
                )
                logger.info(completion_summary)
                execution_log.log_section("Task Breakdown Completion", completion_summary)
                return

            # Validate input structure
            for task_group in high_level_tasks:
                if not ValidationHelper.validate_task_group(task_group):
                    raise ValueError(f"Invalid task group structure: {json.dumps(task_group, indent=2)}")
            
            # Log breakdown summary
            user_stories = [t for t in high_level_tasks if t["high_level_task"]["type"] == "User Story"]
            technical_tasks = [t for t in high_level_tasks if t["high_level_task"]["type"] == "Technical Task"]
            
            summary = (
                f"\nStarting task breakdown:\n"
                f"- Total tasks to break down: {len(high_level_tasks)}\n"
                f"- User Stories: {len(user_stories)}\n"
                f"- Technical Tasks: {len(technical_tasks)}\n"
            )
            logger.info(summary)
            execution_log.log_section("Task Breakdown Summary", summary)
            
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
                    proposed_tickets.add_subtasks(task["name"], subtasks)
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