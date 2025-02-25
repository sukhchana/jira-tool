from typing import Dict, Any, List

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
from utils.config import settings


class UserStoryGenerator:
    """Service responsible for generating user stories from epic analysis"""

    def __init__(self, execution_log: ExecutionLogService):
        self.llm = VertexLLM()
        self.execution_log = execution_log

    async def generate_user_stories(
            self,
            epic_analysis: Dict[str, Any],
            task_tracker: TaskTracker,
            proposed_tickets: ProposedTicketsService
    ) -> List[UserStory]:
        """
        Generate user stories based on epic analysis.
        
        Args:
            epic_analysis: Structured analysis of the epic
            task_tracker: TaskTracker instance to track tasks
            proposed_tickets: ProposedTicketsService instance
            
        Returns:
            List of generated user stories
        
        Raises:
            ValueError: If story parsing fails
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
            response = await self.llm.generate_content(prompt, temperature=0.2)

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

            # Process each user story
            for idx, story in enumerate(parsed_stories, 1):
                story_title = story.get("title", f"Story #{idx}")
                logger.info(f"Processing user story {idx}/{len(parsed_stories)}: {story_title}")

                try:
                    # Generate additional components
                    logger.info(f"Generating research summary for {story_title}")
                    research_summary = await self._generate_research_summary(story)

                    logger.info(f"Generating code examples for {story_title}")
                    code_blocks = await self._generate_code_examples(story)
                    logger.debug(f"Generated {len(code_blocks)} code examples")

                    logger.info(f"Generating Gherkin scenarios for {story_title}")
                    scenarios = await self._generate_gherkin_scenarios(story)
                    logger.debug(f"Generated {len(scenarios)} Gherkin scenarios")

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

                    # Add to tracking systems
                    logger.info(f"Adding {story_title} to task tracker and proposed tickets")
                    try:
                        task_tracker.add_user_story(user_story.model_dump())
                        story_id = proposed_tickets.add_high_level_task(user_story.model_dump())
                        user_story.id = story_id
                    except Exception as e:
                        logger.error(f"Failed to track user story {story_title}: {str(e)}")
                        raise  # Re-raise tracking error

                    # Add to stories list
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
                    logger.error(f"Failed to process user story {story_title}: {str(e)}")
                    logger.exception("Full traceback:")
                    raise

        except Exception as e:
            if not isinstance(e, ValueError):  # Don't log LLM interaction for parsing errors
                logger.error(f"Failed to generate user stories: {str(e)}")
                self.execution_log.log_llm_interaction(
                    "User Story Generation",
                    None,  # No response since an error occurred
                    str(e)
                )
            raise

        logger.info(f"Completed user story generation. Generated {len(stories)} stories")
        return stories

    async def _generate_research_summary(self, story_context: Dict[str, Any]) -> ResearchSummary:
        """Generate research summary for a user story"""
        logger.debug(f"Generating research summary for story: {story_context.get('title')}")

        if not settings.ENABLE_RESEARCH_TASKS:
            logger.debug("Research tasks disabled, skipping LLM call")
            research_data = ResearchSummaryParser.parse("")
            return ResearchSummary(**research_data)

        prompt = UserStoryPromptBuilder.build_research_prompt(story_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing research summary response")
        research_data = ResearchSummaryParser.parse(response)
        return ResearchSummary(**research_data)

    async def _generate_code_examples(self, story_context: Dict[str, Any]) -> List[CodeBlock]:
        """Generate code examples for a user story"""
        logger.debug(f"Generating code examples for story: {story_context.get('title')}")

        if not settings.ENABLE_CODE_BLOCK_GENERATION:
            logger.debug("Code block generation disabled, skipping LLM call")
            return []

        prompt = UserStoryPromptBuilder.build_code_examples_prompt(story_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing code examples response")
        code_blocks_data = CodeBlockParser.parse(response)
        return [CodeBlock(**block) for block in code_blocks_data]

    async def _generate_gherkin_scenarios(self, story_context: Dict[str, Any]) -> List[GherkinScenario]:
        """Generate Gherkin scenarios for a user story"""
        logger.debug(f"Generating Gherkin scenarios for story: {story_context.get('title')}")

        if not settings.ENABLE_GHERKIN_SCENARIOS:
            logger.debug("Gherkin scenarios disabled, skipping LLM call")
            return []

        prompt = UserStoryPromptBuilder.build_gherkin_scenarios_prompt(story_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        logger.debug("Parsing Gherkin scenarios response")
        scenarios_data = GherkinParser.parse(response)
        return [GherkinScenario(**scenario) for scenario in scenarios_data]
