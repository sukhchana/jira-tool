from typing import Dict, Any, List

from loguru import logger

from llm.vertexllm import VertexLLM
from models.technical_task import TechnicalTask, ImplementationApproach
from models.user_story import UserStory
from models.code_block import CodeBlock
from models.gherkin import GherkinScenario
from models.research_summary import ResearchSummary
from parsers import (
    TechnicalTaskParser,
    ResearchSummaryParser,
    CodeBlockParser,
    GherkinParser
)
from prompts.technical_task_prompt_builder import TechnicalTaskPromptBuilder
from services.execution_log_service import ExecutionLogService
from services.proposed_tickets_service import ProposedTicketsService
from services.task_tracker import TaskTracker
from utils.config import settings


class TechnicalTaskGenerator:
    """Service responsible for generating technical tasks from user stories"""

    def __init__(self, execution_log: ExecutionLogService):
        self.llm = VertexLLM()
        self.execution_log = execution_log

    async def generate_technical_tasks(
            self,
            user_stories: List[UserStory],
            epic_analysis: Dict[str, Any],
            task_tracker: TaskTracker,
            proposed_tickets: ProposedTicketsService
    ) -> List[TechnicalTask]:
        """
        Generate technical tasks based on user stories and epic analysis.
        
        Args:
            user_stories: List of user stories to generate technical tasks from
            epic_analysis: Structured analysis of the epic
            task_tracker: TaskTracker instance to track tasks
            proposed_tickets: ProposedTicketsService instance
            
        Returns:
            List of generated technical tasks
        """
        logger.info("Starting technical task generation process")
        tasks = []

        try:
            # Generate technical tasks prompt and get LLM response
            logger.info(f"Generating technical tasks from {len(user_stories)} user stories")
            prompt = TechnicalTaskPromptBuilder.build_technical_tasks_prompt(
                [story.model_dump() for story in user_stories],
                epic_analysis
            )
            
            try:
                response = await self.llm.generate_content(prompt, temperature=0.2)
            except Exception as e:
                # Log the LLM error before re-raising
                self.execution_log.log_llm_interaction(
                    "Technical Task Generation",
                    None,  # No response since an error occurred
                    str(e)
                )
                raise

            # Debug log the response
            logger.debug("Raw LLM response for technical tasks:")
            logger.debug("-" * 80)
            logger.debug(response)
            logger.debug("-" * 80)

            # Parse and process technical tasks
            logger.info("Parsing technical tasks from LLM response")
            parsed_tasks = TechnicalTaskParser.parse_from_response(response)
            logger.info(f"Successfully parsed {len(parsed_tasks)} technical tasks")

            for idx, task_dict in enumerate(parsed_tasks, 1):
                try:
                    task_title = task_dict.get("title", f"Task #{idx}")
                    logger.info(f"Processing technical task {idx}/{len(parsed_tasks)}: {task_title}")

                    # Generate additional components
                    logger.info(f"Generating research summary for {task_title}")
                    research_summary = await self._generate_research_summary(task_dict)

                    logger.info(f"Generating code examples for {task_title}")
                    code_blocks = await self._generate_code_examples(task_dict)
                    logger.debug(f"Generated {len(code_blocks)} code examples")

                    logger.info(f"Generating Gherkin scenarios for {task_title}")
                    scenarios = await self._generate_gherkin_scenarios(task_dict)
                    logger.debug(f"Generated {len(scenarios)} Gherkin scenarios")

                    # Create TechnicalTask model
                    logger.info(f"Creating complete technical task model for {task_title}")
                    task = TechnicalTask(
                        title=task_dict.get("title"),
                        description=task_dict.get("description"),
                        technical_domain=task_dict.get("technical_domain"),
                        complexity=task_dict.get("complexity", "Medium"),
                        business_value=task_dict.get("business_value", "Medium"),
                        story_points=task_dict.get("story_points", 3),
                        dependencies=task_dict.get("dependencies", []),
                        required_skills=task_dict.get("required_skills", []),
                        suggested_assignee=task_dict.get("suggested_assignee", "Unassigned"),
                        type="Technical Task",
                        implementation_approach=ImplementationApproach(
                            architecture=task_dict.get("implementation_approach", {}).get("architecture", "Not specified"),
                            apis=task_dict.get("implementation_approach", {}).get("apis", "Not specified"),
                            database=task_dict.get("implementation_approach", {}).get("database", "Not specified"),
                            security=task_dict.get("implementation_approach", {}).get("security", "Not specified")
                        ),
                        acceptance_criteria=task_dict.get("acceptance_criteria", []),
                        performance_impact=task_dict.get("performance_impact",
                                                         "No significant performance impact expected"),
                        scalability_considerations=task_dict.get("scalability_considerations",
                                                                 "No specific scalability considerations identified"),
                        monitoring_needs=task_dict.get("monitoring_needs", "Standard application monitoring"),
                        testing_requirements=task_dict.get("testing_requirements", "Standard unit and integration tests"),
                        research_summary=research_summary,
                        code_blocks=code_blocks,
                        scenarios=scenarios
                    )

                    # Add to tracking systems
                    logger.info(f"Adding {task_title} to task tracker and proposed tickets")
                    task_tracker.add_technical_task(task.model_dump())
                    task_id = proposed_tickets.add_high_level_task(task.model_dump())
                    task.id = task_id

                    # Add to tasks list
                    tasks.append(task)

                    # Log the task generation
                    logger.info(f"Successfully completed generation of {task_title}")
                    self.execution_log.log_llm_interaction(
                        f"Technical Task Generation - {task.title}",
                        prompt,
                        response,
                        {"technical_task": task.model_dump()}
                    )

                except Exception as e:
                    logger.error(f"Failed to process technical task {task_dict.get('title')}: {str(e)}")
                    logger.exception("Full traceback:")
                    continue

            logger.info(f"Completed technical task generation. Generated {len(tasks)} tasks")
            return tasks

        except Exception as e:
            logger.error(f"Failed to generate technical tasks: {str(e)}")
            logger.exception("Full traceback:")
            return []

    async def _generate_research_summary(self, task_context: Dict[str, Any]) -> ResearchSummary:
        """Generate research summary for a technical task"""
        logger.debug(f"Generating research summary for task: {task_context.get('title')}")

        if not settings.ENABLE_RESEARCH_TASKS:
            logger.debug("Research tasks disabled, skipping LLM call")
            research_data = ResearchSummaryParser.parse("")
            return ResearchSummary(**research_data)

        prompt = TechnicalTaskPromptBuilder.build_technical_task_research_prompt(task_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing research summary response")
        research_data = ResearchSummaryParser.parse(response)
        return ResearchSummary(**research_data)

    async def _generate_code_examples(self, task_context: Dict[str, Any]) -> List[CodeBlock]:
        """Generate code examples for a technical task"""
        logger.debug(f"Generating code examples for task: {task_context.get('title')}")

        if not settings.ENABLE_CODE_BLOCK_GENERATION:
            logger.debug("Code block generation disabled, skipping LLM call")
            return []

        prompt = TechnicalTaskPromptBuilder.build_code_examples_prompt(task_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing code examples response")
        code_blocks_data = CodeBlockParser.parse(response)
        return [CodeBlock(**block) for block in code_blocks_data]

    async def _generate_gherkin_scenarios(self, task_context: Dict[str, Any]) -> List[GherkinScenario]:
        """Generate Gherkin scenarios for a technical task"""
        logger.debug(f"Generating Gherkin scenarios for task: {task_context.get('title')}")

        if not settings.ENABLE_GHERKIN_SCENARIOS:
            logger.debug("Gherkin scenarios disabled, skipping LLM call")
            return []

        prompt = TechnicalTaskPromptBuilder.build_gherkin_scenarios_prompt(task_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing Gherkin scenarios response")
        scenarios_data = GherkinParser.parse(response)
        return [GherkinScenario(**scenario) for scenario in scenarios_data]
