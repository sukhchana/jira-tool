import json
from typing import Dict, Any, List, Union

from loguru import logger

from llm.vertexllm import VertexLLM
from models.sub_task import SubTask
from models.technical_task import TechnicalTask
from models.user_story import UserStory
from parsers import SubtaskParser
from prompts.subtask_prompt_builder import SubtaskPromptBuilder
from services.execution_log_service import ExecutionLogService
from services.proposed_tickets_service import ProposedTicketsService
from services.task_tracker import TaskTracker
from utils.config import settings
from utils.json_sanitizer import JSONSanitizer


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
        logger.info("Starting subtask breakdown process")
        logger.info(f"Breaking down {len(high_level_tasks)} high-level tasks")
        all_subtasks: List[SubTask] = []

        try:
            # Process each task
            for task_idx, task in enumerate(high_level_tasks, 1):
                try:
                    task_dict = task.model_dump()
                    logger.info(f"Breaking down task {task_idx}/{len(high_level_tasks)}: {task.title} ({task.type})")

                    # Generate base subtasks
                    logger.info(f"Generating base subtasks for {task.title}")
                    subtasks = await self._generate_subtasks(task_dict, epic_details)
                    logger.info(f"Generated {len(subtasks)} base subtasks for {task.title}")

                    # For each subtask, enrich with additional details
                    logger.info(f"Enriching {len(subtasks)} subtasks with additional details")
                    for subtask_idx, subtask in enumerate(subtasks, 1):
                        subtask_title = subtask.title
                        logger.info(f"Processing subtask {subtask_idx}/{len(subtasks)}: {subtask_title}")

                        subtask_context = {
                            **subtask.model_dump(),
                            "parent_task": task_dict,
                            "epic_details": epic_details
                        }

                        # Generate implementation approach
                        logger.info(f"Generating implementation approach for {subtask_title}")
                        impl_approach = await self._generate_implementation_approach(subtask_context)
                        if impl_approach:
                            logger.debug(f"Adding implementation approach to {subtask_title}")
                            subtask.description = self._combine_description(
                                subtask.description,
                                impl_approach
                            )

                        # Generate code examples
                        logger.info(f"Generating code examples for {subtask_title}")
                        code_examples = await self._generate_code_examples(subtask_context)
                        if code_examples:
                            logger.debug(f"Generated {len(code_examples)} code examples for {subtask_title}")
                            subtask.description = self._combine_description(
                                subtask.description,
                                "\n\nCode Examples:\n" + self._format_code_examples(code_examples)
                            )

                        # Generate testing plan
                        logger.info(f"Generating testing plan for {subtask_title}")
                        testing_plan = await self._generate_testing_plan(subtask_context)
                        if testing_plan:
                            test_criteria = self._extract_test_criteria(testing_plan)
                            logger.debug(f"Adding {len(test_criteria)} test criteria to {subtask_title}")
                            subtask.acceptance_criteria.extend(test_criteria)

                        # Generate research summary
                        logger.info(f"Generating research summary for {subtask_title}")
                        research_summary = await self._generate_research_summary(subtask_context)
                        if research_summary:
                            logger.debug(f"Adding research summary to {subtask_title}")
                            subtask.description = self._combine_description(
                                subtask.description,
                                "\n\nTechnical Research:\n" + self._format_research_summary(research_summary)
                            )

                        logger.info(f"Completed enrichment of subtask: {subtask_title}")

                    # Add to all subtasks list
                    all_subtasks.extend(subtasks)

                    # Log the breakdown
                    logger.info(f"Logging breakdown details for {task.title}")
                    self.execution_log.log_section(
                        f"Subtasks for {task.title}",
                        json.dumps({
                            "parent_task": task.title,
                            "parent_type": task.type,
                            "subtask_count": len(subtasks),
                            "total_points": sum(st.story_points for st in subtasks),
                            "subtasks": [st.model_dump() for st in subtasks]
                        }, indent=2)
                    )

                    # Add subtasks to tracking systems
                    logger.info(f"Adding subtasks to tracking systems for {task.title}")
                    task_tracker.add_subtasks(task.title, [st.model_dump() for st in subtasks])
                    proposed_tickets.add_subtasks(
                        parent_name=task.title,
                        subtasks=[st.model_dump() for st in subtasks],
                        parent_id=task.id
                    )

                    logger.info(f"Completed breakdown for {task.title} - {len(subtasks)} subtasks created")

                except Exception as e:
                    error_msg = f"Failed to break down task {task.title}"
                    logger.error(f"{error_msg}: {str(e)}")
                    logger.error(f"Task details: {json.dumps(task.model_dump(), indent=2)}")
                    logger.exception("Full traceback:")
                    raise

            logger.info(f"Completed subtask breakdown process. Generated {len(all_subtasks)} total subtasks")
            return all_subtasks

        except Exception as e:
            logger.error(f"Failed to break down tasks: {str(e)}")
            logger.error(f"High-level tasks: {json.dumps([t.model_dump() for t in high_level_tasks], indent=2)}")
            logger.exception("Full traceback:")
            raise

    async def _generate_subtasks(
            self,
            parent_task: Dict[str, Any],
            epic_details: Dict[str, Any]
    ) -> List[SubTask]:
        """Generate base subtasks for a high-level task"""
        try:
            logger.debug(f"Building subtasks prompt for {parent_task.get('title')}")
            prompt = SubtaskPromptBuilder.build_subtasks_prompt(parent_task, epic_details)

            logger.debug("Calling LLM for subtask generation")
            response = await self.llm.generate_content(prompt)

            logger.debug("Raw LLM response for subtasks:")
            logger.debug("-" * 80)
            logger.debug(response)
            logger.debug("-" * 80)

            logger.debug("Parsing subtasks from LLM response")
            subtasks = SubtaskParser.parse(response)
            logger.debug(f"Successfully parsed {len(subtasks)} subtasks")

            return subtasks

        except Exception as e:
            logger.error(f"Failed to generate subtasks: {str(e)}")
            logger.error(f"Parent task: {json.dumps(parent_task, indent=2)}")
            logger.exception("Full traceback:")
            raise

    async def _generate_implementation_approach(self, subtask_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate implementation approach details"""
        try:
            logger.debug(f"Generating implementation approach for subtask: {subtask_context.get('title')}")

            if not settings.ENABLE_IMPLEMENTATION_APPROACH:
                logger.debug("Implementation approach disabled, skipping LLM call")
                return {}

            prompt = SubtaskPromptBuilder.build_implementation_approach_prompt(subtask_context)
            response = await self.llm.generate_content(prompt)
            logger.debug("Parsing implementation approach response")
            return JSONSanitizer.safe_parse_with_fallback(response)
        except Exception as e:
            logger.error(f"Failed to generate implementation approach: {str(e)}")
            logger.exception("Full traceback:")
            return None

    async def _generate_code_examples(self, subtask_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate code examples"""
        try:
            logger.debug(f"Generating code examples for subtask: {subtask_context.get('title')}")

            if not settings.ENABLE_CODE_BLOCK_GENERATION:
                logger.debug("Code block generation disabled, skipping LLM call")
                return []

            prompt = SubtaskPromptBuilder.build_code_examples_prompt(subtask_context)
            response = await self.llm.generate_content(prompt)
            logger.debug("Parsing code examples response")
            return JSONSanitizer.safe_parse_with_fallback(response, [])
        except Exception as e:
            logger.error(f"Failed to generate code examples: {str(e)}")
            logger.exception("Full traceback:")
            return []

    async def _generate_testing_plan(self, subtask_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate testing plan"""
        try:
            logger.debug(f"Generating testing plan for subtask: {subtask_context.get('title')}")

            if not settings.ENABLE_TEST_PLANS:
                logger.debug("Test plan generation disabled, skipping LLM call")
                return {}

            prompt = SubtaskPromptBuilder.build_testing_plan_prompt(subtask_context)
            response = await self.llm.generate_content(prompt)
            logger.debug("Parsing testing plan response")
            return JSONSanitizer.safe_parse_with_fallback(response)
        except Exception as e:
            logger.error(f"Failed to generate testing plan: {str(e)}")
            logger.exception("Full traceback:")
            return None

    async def _generate_research_summary(self, subtask_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate research summary"""
        try:
            logger.debug(f"Generating research summary for subtask: {subtask_context.get('title')}")

            if not settings.ENABLE_RESEARCH_TASKS:
                logger.debug("Research tasks disabled, skipping LLM call")
                return {}

            prompt = SubtaskPromptBuilder.build_research_summary_prompt(subtask_context)
            response = await self.llm.generate_content(prompt)
            logger.debug("Parsing research summary response")
            return JSONSanitizer.safe_parse_with_fallback(response)
        except Exception as e:
            logger.error(f"Failed to generate research summary: {str(e)}")
            logger.exception("Full traceback:")
            return None

    def _combine_description(self, base_description: str, additional_content: str) -> str:
        """Combine base description with additional content"""
        if not additional_content:
            return base_description
        return f"{base_description}\n\n{additional_content}"

    def _format_code_examples(self, code_examples: List[Dict[str, Any]]) -> str:
        """Format code examples into markdown"""
        if not code_examples:
            return ""

        formatted = []
        for example in code_examples:
            formatted.append(
                f"### {example.get('description', 'Code Example')}\n"
                f"```{example.get('language', 'text')}\n"
                f"{example.get('code', '')}\n"
                f"```\n"
            )
        return "\n".join(formatted)

    def _extract_test_criteria(self, testing_plan: Dict[str, Any]) -> List[str]:
        """Extract acceptance criteria from testing plan"""
        criteria = []

        # Add unit test scenarios
        for test in testing_plan.get("unit_tests", []):
            criteria.append(f"Unit Test: {test}")

        # Add integration test scenarios
        for test in testing_plan.get("integration_tests", []):
            criteria.append(f"Integration Test: {test}")

        # Add edge cases
        for case in testing_plan.get("edge_cases", []):
            criteria.append(f"Edge Case: {case}")

        return criteria

    def _format_research_summary(self, research: Dict[str, Any]) -> str:
        """Format research summary into markdown sections"""
        sections = []

        if research.get("pain_points"):
            sections.append(f"**Technical Challenges:**\n{research['pain_points']}")

        if research.get("success_metrics"):
            sections.append(f"**Success Metrics:**\n{research['success_metrics']}")

        if research.get("modern_approaches"):
            sections.append(f"**Implementation Approach:**\n{research['modern_approaches']}")

        if research.get("performance_considerations"):
            sections.append(f"**Performance Considerations:**\n{research['performance_considerations']}")

        if research.get("security_implications"):
            sections.append(f"**Security Considerations:**\n{research['security_implications']}")

        return "\n\n".join(sections)
