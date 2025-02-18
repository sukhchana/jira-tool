from typing import Dict, Any, List
from fastapi import HTTPException
from services.jira_service import JiraService
from loguru import logger
from datetime import datetime
import os

class JiraOrchestrationService:
    """
    Service responsible for orchestrating JIRA ticket creation and relationships.
    
    This service handles:
    - Creating hierarchical ticket structures (Epic -> Story -> Subtask)
    - Managing ticket relationships
    - Setting ticket metadata (story points, labels, etc.)
    - Maintaining consistent ticket formatting
    """

    def __init__(self):
        """Initialize the JIRA service"""
        logger.info("Initializing JiraOrchestrationService")
        self.jira_service = JiraService()
        logger.info("Successfully initialized JiraOrchestrationService")

    async def create_epic_breakdown_structure(
        self,
        epic_key: str,
        breakdown: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create a complete JIRA ticket hierarchy from an epic breakdown.

        Flow:
        1. Validate epic exists and breakdown structure
        2. Create stories for high-level tasks
        3. Create subtasks for detailed tasks
        4. Establish ticket relationships
        5. Set metadata and labels

        Args:
            epic_key: The parent epic's key
            breakdown: The epic breakdown structure from LLM

        Returns:
            List of all created JIRA tickets with their relationships

        Raises:
            HTTPException: If ticket creation or linking fails
        """
        try:
            logger.info(f"Creating JIRA ticket hierarchy for epic {epic_key}")
            created_tickets = []
            project_key = epic_key.split("-")[0]

            # Verify epic exists
            await self.jira_service.get_ticket(epic_key)

            for task_group in breakdown["tasks"]:
                story = await self._create_story(
                    project_key=project_key,
                    epic_key=epic_key,
                    task=task_group["high_level_task"]
                )
                created_tickets.append(story)

                subtasks = await self._create_subtasks(
                    project_key=project_key,
                    story_key=story["key"],
                    subtasks=task_group["subtasks"]
                )
                created_tickets.extend(subtasks)

            logger.success(
                f"Successfully created ticket hierarchy: "
                f"{len(created_tickets)} tickets total"
            )
            return created_tickets

        except Exception as e:
            logger.error(f"Failed to create JIRA ticket hierarchy: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create JIRA ticket hierarchy: {str(e)}"
            )

    async def _create_story(
        self,
        project_key: str,
        epic_key: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a story-level ticket linked to an epic"""
        logger.debug(f"Creating story from task: {task['title']}")
        
        story = await self.jira_service.create_ticket(
            project_key=project_key,
            summary=task["title"],
            description=self._format_story_description(task),
            issue_type="Story",
            labels=[task["technical_domain"], f"complexity-{task['complexity'].lower()}"],
            parent_key=epic_key
        )
        
        logger.debug(f"Created story {story['key']}")
        return story

    async def _create_subtasks(
        self,
        project_key: str,
        story_key: str,
        subtasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create subtasks linked to a story"""
        logger.debug(f"Creating {len(subtasks)} subtasks for story {story_key}")
        created_subtasks = []

        for subtask in subtasks:
            task = await self.jira_service.create_ticket(
                project_key=project_key,
                summary=subtask["title"],
                description=self._format_subtask_description(subtask),
                issue_type="Sub-task",
                parent_key=story_key,
                story_points=subtask["story_points"],
                labels=subtask["required_skills"]
            )
            created_subtasks.append(task)
            logger.debug(f"Created subtask {task['key']}")

        return created_subtasks

    def _format_story_description(self, task: Dict[str, Any]) -> str:
        """Format the description for a story ticket"""
        return (
            f"{task['description']}\n\n"
            f"Technical Domain: {task['technical_domain']}\n"
            f"Complexity: {task['complexity']}\n"
            f"Dependencies: {', '.join(task['dependencies']) if task['dependencies'] else 'None'}"
        )

    def _format_subtask_description(self, subtask: Dict[str, Any]) -> str:
        """Format the description for a subtask ticket"""
        return (
            f"{subtask['description']}\n\n"
            f"Acceptance Criteria:\n{subtask['acceptance_criteria']}\n\n"
            f"Required Skills: {', '.join(subtask['required_skills'])}\n"
            f"Story Points: {subtask['story_points']}\n"
            f"Suggested Assignee Type: {subtask['suggested_assignee']}\n\n"
            f"Dependencies: {', '.join(subtask['dependencies']) if subtask['dependencies'] else 'None'}"
        )

    async def create_execution_plan(
        self,
        epic_key: str,
        breakdown: Dict[str, Any]
    ) -> str:
        """
        Generate a markdown execution plan for the epic breakdown.
        Instead of creating tickets, generates a detailed markdown file
        showing what would be created.

        Args:
            epic_key: The parent epic's key
            breakdown: The epic breakdown structure from LLM

        Returns:
            Path to the generated markdown file

        Raises:
            HTTPException: If plan generation fails
        """
        try:
            logger.info(f"Generating execution plan for epic {epic_key}")
            
            # Create execution plans directory if it doesn't exist
            os.makedirs("execution_plans", exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"execution_plans/EXECUTION_{epic_key}_{timestamp}.md"
            
            # Build the markdown content
            content = self._generate_execution_plan_content(epic_key, breakdown)
            
            # Write to file
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.success(f"Successfully generated execution plan: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to generate execution plan: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate execution plan: {str(e)}"
            )

    def _generate_execution_plan_content(
        self,
        epic_key: str,
        breakdown: Dict[str, Any]
    ) -> str:
        """Generate the markdown content for the execution plan"""
        
        lines = [
            f"# Execution Plan for Epic {epic_key}",
            "",
            "## Epic Details",
            f"- Key: {epic_key}",
            f"- Summary: {breakdown['epic_summary']}",
            "",
            "## Epic Analysis",
            self._format_dict_as_markdown(breakdown['analysis']),
            "",
            "## Proposed Ticket Structure",
            "",
            "The following tickets will be created:",
            ""
        ]

        total_stories = len(breakdown["tasks"])
        total_subtasks = sum(len(task_group["subtasks"]) for task_group in breakdown["tasks"])
        
        lines.extend([
            "### Summary",
            f"- Total Stories to create: {total_stories}",
            f"- Total Subtasks to create: {total_subtasks}",
            "",
            "### Detailed Breakdown",
            ""
        ])

        # Add each story and its subtasks
        for task_group in breakdown["tasks"]:
            story = task_group["high_level_task"]
            lines.extend([
                "---",
                "",
                f"#### Story: {story['title']}",
                "```",
                f"Type: Story",
                f"Technical Domain: {story['technical_domain']}",
                f"Complexity: {story['complexity']}",
                "",
                "Description:",
                self._format_story_description(story),
                "```",
                "",
                "##### Subtasks:",
                ""
            ])

            for subtask in task_group["subtasks"]:
                lines.extend([
                    f"###### {subtask['title']}",
                    "```",
                    f"Type: Sub-task",
                    f"Story Points: {subtask['story_points']}",
                    f"Suggested Assignee: {subtask['suggested_assignee']}",
                    "",
                    "Description:",
                    self._format_subtask_description(subtask),
                    "```",
                    ""
                ])

        # Add execution notes
        lines.extend([
            "## Execution Notes",
            "1. All stories will be linked to the parent epic",
            "2. All subtasks will be linked to their respective stories",
            "3. Labels and story points will be set as specified",
            "4. Technical domains will be added as labels",
            "",
            "## Validation Steps",
            "1. Verify epic exists and is accessible",
            "2. Verify project permissions",
            "3. Verify custom fields (story points, etc.) are available",
            "4. Verify issue types (Story, Sub-task) are available",
            "",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])

        return "\n".join(lines)

    def _format_dict_as_markdown(self, d: Dict[str, Any]) -> str:
        """Format a dictionary as markdown list items"""
        lines = []
        for key, value in d.items():
            formatted_key = key.replace("_", " ").title()
            if isinstance(value, list):
                lines.append(f"### {formatted_key}")
                lines.extend([f"- {item}" for item in value])
            else:
                lines.append(f"### {formatted_key}")
                lines.append(str(value))
            lines.append("")
        return "\n".join(lines) 