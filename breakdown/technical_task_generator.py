from typing import Dict, Any, List
import asyncio
from asyncio import Semaphore

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
from utils.config import settings, Settings
from utils.json_sanitizer import JSONSanitizer
from llm.llm_service_factory import get_llm_service


class TechnicalTaskGenerator:
    """Service responsible for generating technical tasks from user stories"""

    def __init__(self, execution_log: ExecutionLogService):
        """Initialize with dependencies"""
        self.execution_log = execution_log
        self.llm_service = get_llm_service()
        self.settings = settings  # Default settings
        
    def set_config(self, config: Settings):
        """Override default settings with provided configuration
        
        Args:
            config: Settings object with feature flag settings
        """
        if not config:
            return
            
        self.settings = config
        logger.debug(f"TechnicalTaskGenerator settings updated: {vars(self.settings)}")

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
                response = await self.llm_service.generate_content(prompt, temperature=0.2)
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

            # Enrich and process technical tasks in parallel
            enriched_tasks = await self._enrich_technical_tasks_parallel(parsed_tasks, prompt, response)
            
            # Add enriched tasks to tracking systems and the result list
            for task in enriched_tasks:
                task_title = task.title
                
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

            logger.info(f"Completed technical task generation. Generated {len(tasks)} tasks")
            return tasks

        except Exception as e:
            logger.error(f"Failed to generate technical tasks: {str(e)}")
            logger.exception("Full traceback:")
            raise
            
    async def _enrich_technical_tasks_parallel(
            self, 
            parsed_tasks: List[Dict[str, Any]], 
            prompt: str, 
            response: str, 
            max_concurrency: int = 4
    ) -> List[TechnicalTask]:
        """
        Enrich multiple technical tasks with additional details in parallel.
        
        Args:
            parsed_tasks: List of parsed technical task dictionaries
            prompt: The original prompt used to generate the tasks
            response: The LLM response containing the tasks
            max_concurrency: Maximum number of concurrent enrichment operations
            
        Returns:
            List of enriched TechnicalTask objects
        """
        # Use a semaphore to limit concurrency
        semaphore = Semaphore(max_concurrency)
        
        async def enrich_task(task_dict: Dict[str, Any], idx: int) -> TechnicalTask:
            async with semaphore:
                task_title = task_dict.get("title", f"Task #{idx}")
                logger.info(f"Processing technical task {idx}/{len(parsed_tasks)} in parallel: {task_title}")
                
                try:
                    # Generate additional components in parallel
                    research_summary, code_blocks, scenarios = await asyncio.gather(
                        self._generate_research_summary(task_dict),
                        self._generate_code_examples(task_dict),
                        self._generate_gherkin_scenarios(task_dict)
                    )
                    
                    logger.debug(f"Generated research summary for {task_title}")
                    logger.debug(f"Generated {len(code_blocks)} code examples for {task_title}")
                    logger.debug(f"Generated {len(scenarios)} Gherkin scenarios for {task_title}")
                    
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
                    
                    return task
                    
                except Exception as e:
                    logger.error(f"Failed to process technical task {task_title}: {str(e)}")
                    logger.exception("Full traceback:")
                    raise
        
        # Create tasks for all technical tasks
        enrichment_tasks = []
        for idx, task_dict in enumerate(parsed_tasks, 1):
            enrichment_tasks.append(enrich_task(task_dict, idx))
        
        # Run all tasks and gather results
        results = await asyncio.gather(*enrichment_tasks, return_exceptions=True)
        
        # Filter out exceptions and return successfully enriched tasks
        enriched_tasks = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task enrichment failed: {str(result)}")
            else:
                enriched_tasks.append(result)
        
        return enriched_tasks

    async def _generate_research_summary(self, task_context: Dict[str, Any]) -> ResearchSummary:
        """Generate research summary for a technical task"""
        try:
            logger.debug(f"Generating research summary for task: {task_context.get('title')}")

            if not self.settings.ENABLE_RESEARCH_TASKS:
                logger.debug("Research tasks disabled, skipping LLM call")
                return ResearchSummary(
                    pain_points="",
                    success_metrics="",
                    similar_implementations="",
                    modern_approaches=""
                )

            prompt = TechnicalTaskPromptBuilder.build_technical_task_research_prompt(task_context)
            response = await self.llm_service.generate_content(prompt)
            logger.debug("Parsing research summary response")
            raw_data = JSONSanitizer.safe_parse_with_fallback(response)
            
            if not raw_data:
                return ResearchSummary(
                    pain_points="",
                    success_metrics="",
                    similar_implementations="",
                    modern_approaches=""
                )
            
            return ResearchSummary(**raw_data)
        except Exception as e:
            logger.error(f"Failed to generate research summary: {str(e)}")
            logger.exception("Full traceback:")
            return ResearchSummary(
                pain_points="",
                success_metrics="",
                similar_implementations="",
                modern_approaches=""
            )

    async def _generate_code_examples(self, task_context: Dict[str, Any]) -> List[CodeBlock]:
        """Generate code examples for a technical task"""
        logger.debug(f"Generating code examples for task: {task_context.get('title')}")

        if not self.settings.ENABLE_CODE_BLOCK_GENERATION:
            logger.debug("Code block generation disabled, skipping LLM call")
            return []

        prompt = TechnicalTaskPromptBuilder.build_code_examples_prompt(task_context)
        response = await self.llm_service.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing code examples response")
        code_blocks_data = CodeBlockParser.parse(response)
        return [CodeBlock(**block) for block in code_blocks_data]

    async def _generate_gherkin_scenarios(self, task_context: Dict[str, Any]) -> List[GherkinScenario]:
        """Generate Gherkin scenarios for a technical task"""
        logger.debug(f"Generating Gherkin scenarios for task: {task_context.get('title')}")

        if not self.settings.ENABLE_GHERKIN_SCENARIOS:
            logger.debug("Gherkin scenarios disabled, skipping LLM call")
            return []

        prompt = TechnicalTaskPromptBuilder.build_gherkin_scenarios_prompt(task_context)
        response = await self.llm_service.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing Gherkin scenarios response")
        scenarios_data = GherkinParser.parse(response)
        return [GherkinScenario(**scenario) for scenario in scenarios_data]
