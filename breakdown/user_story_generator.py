from typing import Dict, Any, List
import asyncio
from asyncio import Semaphore

from loguru import logger

from llm.vertexllm import VertexLLM
from models.code_block import CodeBlock
from models.gherkin import GherkinScenario
from models.research_summary import ResearchSummary
from models.user_story import UserStory
from parsers import (
    ResearchSummaryParser,
    CodeBlockParser,
    GherkinParser,
    UserStoryParser
)
from prompts.user_story_prompt_builder import UserStoryPromptBuilder
from services.execution_log_service import ExecutionLogService
from services.proposed_tickets_service import ProposedTicketsService
from services.task_tracker import TaskTracker
from utils.config import settings, Settings
from utils.json_sanitizer import JSONSanitizer
from llm.llm_service_factory import get_llm_service


class UserStoryGenerator:
    """Service responsible for generating user stories from epic analysis"""

    def __init__(self, execution_log: ExecutionLogService):
        """Initialize the service with required dependencies"""
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
        logger.debug(f"UserStoryGenerator settings updated: {vars(self.settings)}")

    async def generate_user_stories(
            self,
            epic_analysis: Dict[str, Any],
            task_tracker: TaskTracker,
            proposed_tickets: ProposedTicketsService
    ) -> List[UserStory]:
        """
        Generate user stories based on the epic analysis.
        
        Args:
            epic_analysis: Analysis information about the epic
            task_tracker: TaskTracker instance
            proposed_tickets: ProposedTicketsService instance
            
        Returns:
            List of UserStory objects
            
        Raises:
            Exception: If tracking operations fail
        """
        logger.info("Starting user story generation process")
        stories = []

        # Check for empty epic analysis
        if not epic_analysis.get("main_objective") and not epic_analysis.get("technical_domains"):
            logger.info("Empty epic analysis detected")
            self.execution_log.log_section(
                "User Story Generation",
                "No user stories generated: Empty epic analysis"
            )
            return []

        try:
            # Generate base user stories prompt and get LLM response
            logger.info("Generating base user stories from epic analysis")
            prompt = UserStoryPromptBuilder.build_user_stories_prompt(epic_analysis)
            response = await self.llm_service.generate_content(prompt, temperature=0.2)

            # Debug log the response
            logger.debug("Raw LLM response for user stories:")
            logger.debug("-" * 80)
            logger.debug(response)
            logger.debug("-" * 80)

            # Parse base user stories
            logger.info("Parsing base user stories from LLM response")
            try:
                parsed_stories = UserStoryParser.parse_from_response(response)
            except ValueError as e:
                logger.error(f"Failed to parse user stories: {str(e)}")
                self.execution_log.log_section(
                    "User Story Generation Error",
                    "Failed to parse user stories from LLM response"
                )
                raise  # Re-raise ValueError

            logger.info(f"Successfully parsed {len(parsed_stories)} user stories")
            
            # Enrich and process user stories in parallel
            enriched_stories = await self._enrich_user_stories_parallel(parsed_stories)
            
            # Add enriched stories to tracking systems
            for user_story in enriched_stories:
                story_title = user_story.title
                logger.info(f"Adding {story_title} to task tracker and proposed tickets")
                try:
                    task_tracker.add_user_story(user_story.model_dump())
                    story_id = proposed_tickets.add_high_level_task(user_story.model_dump())
                    user_story.id = story_id
                except Exception as e:
                    logger.error(f"Failed to track user story {story_title}: {str(e)}")
                    raise  # Re-raise tracking error
                
                stories.append(user_story)
                
                # Log the story generation
                logger.info(f"Successfully completed generation of {story_title}")
                self.execution_log.log_llm_interaction(
                    f"User Story Generation - {user_story.title}",
                    prompt,
                    response,
                    {"user_story": user_story.model_dump()}
                )

        except Exception as e:
            if not isinstance(e, ValueError):  # Don't log LLM interaction for parsing errors
                logger.error(f"Failed to generate user stories: {str(e)}")
                self.execution_log.log_llm_interaction(
                    "User Story Generation",
                    None,  # No response since an error occurred
                    str(e)
                )
            raise

        return stories
        
    async def _enrich_user_stories_parallel(self, parsed_stories: List[Dict[str, Any]], max_concurrency: int = 4) -> List[UserStory]:
        """
        Enrich multiple user stories with additional details in parallel.
        
        Args:
            parsed_stories: List of parsed user story dictionaries
            max_concurrency: Maximum number of concurrent enrichment operations
            
        Returns:
            List of enriched UserStory objects
        """
        # Use a semaphore to limit concurrency
        semaphore = Semaphore(max_concurrency)
        
        async def enrich_story(story: Dict[str, Any], idx: int) -> UserStory:
            async with semaphore:
                story_title = story.get("title", f"Story #{idx}")
                logger.info(f"Processing user story {idx}/{len(parsed_stories)} in parallel: {story_title}")
                
                try:
                    # Generate additional components in parallel
                    research_summary, code_blocks, scenarios = await asyncio.gather(
                        self._generate_research_summary(story),
                        self._generate_code_examples(story),
                        self._generate_gherkin_scenarios(story)
                    )
                    
                    logger.debug(f"Generated research summary for {story_title}")
                    logger.debug(f"Generated {len(code_blocks)} code examples for {story_title}")
                    logger.debug(f"Generated {len(scenarios)} Gherkin scenarios for {story_title}")
                    
                    # Create complete user story
                    logger.info(f"Creating complete user story model for {story_title}")
                    user_story = UserStory(
                        title=story.get("title"),
                        description=story.get("description"),
                        technical_domain=story.get("technical_domain"),
                        complexity=story.get("complexity", "Medium"),
                        business_value=story.get("business_value", "Medium"),
                        dependencies=story.get("dependencies", []),
                        required_skills=story.get("required_skills", []),
                        suggested_assignee=story.get("suggested_assignee", "Unassigned"),
                        research_summary=research_summary,
                        code_blocks=code_blocks,
                        scenarios=scenarios
                    )
                    
                    return user_story
                    
                except Exception as e:
                    logger.error(f"Failed to process user story {story_title}: {str(e)}")
                    logger.exception("Full traceback:")
                    raise
        
        # Create tasks for all stories
        tasks = [enrich_story(story, idx) for idx, story in enumerate(parsed_stories, 1)]
        
        # Run all tasks and gather results
        enriched_stories = await asyncio.gather(*tasks)
        
        return list(enriched_stories)

    async def _generate_research_summary(self, story_context: Dict[str, Any]) -> ResearchSummary:
        """Generate research summary for a user story"""
        try:
            logger.debug(f"Generating research summary for story: {story_context.get('title')}")

            if not self.settings.ENABLE_RESEARCH_TASKS:
                logger.debug("Research tasks disabled, skipping LLM call")
                return ResearchSummary(
                    pain_points="",
                    success_metrics="",
                    similar_implementations="",
                    modern_approaches=""
                )

            prompt = UserStoryPromptBuilder.build_research_prompt(story_context)
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

    async def _generate_code_examples(self, story_context: Dict[str, Any]) -> List[CodeBlock]:
        """Generate code examples for a user story"""
        logger.debug(f"Generating code examples for story: {story_context.get('title')}")

        if not self.settings.ENABLE_CODE_BLOCK_GENERATION:
            logger.debug("Code block generation disabled, skipping LLM call")
            return []

        prompt = UserStoryPromptBuilder.build_code_examples_prompt(story_context)
        response = await self.llm_service.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing code examples response")
        code_blocks_data = CodeBlockParser.parse(response)
        return [CodeBlock(**block) for block in code_blocks_data]

    async def _generate_gherkin_scenarios(self, story_context: Dict[str, Any]) -> List[GherkinScenario]:
        """Generate Gherkin scenarios for a user story"""
        logger.debug(f"Generating Gherkin scenarios for story: {story_context.get('title')}")

        if not self.settings.ENABLE_GHERKIN_SCENARIOS:
            logger.debug("Gherkin scenarios disabled, skipping LLM call")
            return []

        prompt = UserStoryPromptBuilder.build_gherkin_scenarios_prompt(story_context)
        response = await self.llm_service.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing Gherkin scenarios response")
        scenarios_data = GherkinParser.parse(response)
        return [GherkinScenario(**scenario) for scenario in scenarios_data]
