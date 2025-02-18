from typing import Dict, Any, List
from loguru import logger
from prompts.user_story_prompt_builder import UserStoryPromptBuilder
from services.task_tracker import TaskTracker
from services.proposed_tickets_service import ProposedTicketsService
from services.execution_log_service import ExecutionLogService
from llm.vertexllm import VertexLLM
from models.user_story import UserStory, ResearchSummary, CodeBlock, GherkinScenario
from parsers import (
    ResearchSummaryParser,
    CodeBlockParser,
    GherkinParser,
    UserStoryParser
)
import json

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
        """
        stories = []
        
        # Generate base user stories prompt and get LLM response
        prompt = UserStoryPromptBuilder.build_user_stories_prompt(epic_analysis)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        
        # Debug log the response
        logger.debug("Raw LLM response for user stories:")
        logger.debug("-" * 80)
        logger.debug(response)
        logger.debug("-" * 80)
        
        # Parse base user stories
        parsed_stories = UserStoryParser.parse_from_response(response)
        
        # Debug log the parsing results
        logger.debug(f"Parsed {len(parsed_stories)} stories")
        
        # Process each user story
        for story in parsed_stories:
            try:
                # Generate additional components
                research_summary = await self._generate_research_summary(story)
                code_blocks = await self._generate_code_examples(story)
                scenarios = await self._generate_gherkin_scenarios(story)
                
                # Create complete user story
                user_story = UserStory(
                    title=story.get("title"),
                    description=story.get("description"),
                    technical_domain=story.get("technical_domain"),
                    complexity=story.get("complexity", "Medium"),
                    business_value=story.get("business_value", "Medium"),
                    dependencies=story.get("dependencies", []),
                    research_summary=research_summary,
                    code_blocks=code_blocks,
                    scenarios=scenarios
                )
                
                # Add to tracking systems
                task_tracker.add_user_story(user_story.dict())
                story_id = proposed_tickets.add_high_level_task(user_story.dict())
                user_story.id = story_id
                
                # Add to stories list
                stories.append(user_story)
                
                # Log the story generation
                self.execution_log.log_llm_interaction(
                    f"User Story Generation - {user_story.title}",
                    prompt,
                    response,
                    {"user_story": user_story.dict()}
                )
                
            except Exception as e:
                logger.error(f"Failed to process user story {story.get('title')}: {str(e)}")
                continue
        
        return stories

    async def _generate_research_summary(self, story_context: Dict[str, Any]) -> ResearchSummary:
        """Generate research summary for a user story"""
        prompt = UserStoryPromptBuilder.build_research_prompt(story_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        
        research_data = ResearchSummaryParser.parse(response)
        return ResearchSummary(**research_data)

    async def _generate_code_examples(self, story_context: Dict[str, Any]) -> List[CodeBlock]:
        """Generate code examples for a user story"""
        prompt = UserStoryPromptBuilder.build_code_examples_prompt(story_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        
        code_blocks_data = CodeBlockParser.parse(response)
        return [CodeBlock(**block) for block in code_blocks_data]

    async def _generate_gherkin_scenarios(self, story_context: Dict[str, Any]) -> List[GherkinScenario]:
        """Generate Gherkin scenarios for a user story"""
        prompt = UserStoryPromptBuilder.build_gherkin_scenarios_prompt(story_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        
        scenarios_data = GherkinParser.parse(response)
        return [GherkinScenario(**scenario) for scenario in scenarios_data] 