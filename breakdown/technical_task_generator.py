from typing import Dict, Any, List
from loguru import logger
from prompts.technical_task_prompt_builder import TechnicalTaskPromptBuilder
from services.task_tracker import TaskTracker
from services.proposed_tickets_service import ProposedTicketsService
from services.execution_log_service import ExecutionLogService
from llm.vertexllm import VertexLLM
from models.technical_task import TechnicalTask, ImplementationApproach
from models.user_story import UserStory, ResearchSummary, CodeBlock, GherkinScenario
from parsers import (
    TechnicalTaskParser,
    ResearchSummaryParser,
    CodeBlockParser,
    GherkinParser
)
import json

class TechnicalTaskGenerator:
    """Service responsible for generating technical tasks based on user stories"""
    
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
        tasks = []
        
        # Generate technical tasks prompt and get LLM response
        prompt = TechnicalTaskPromptBuilder.build_technical_tasks_prompt(
            [story.dict() for story in user_stories], 
            epic_analysis
        )
        response = await self.llm.generate_content(prompt, temperature=0.2)
        
        # Debug log the response
        logger.debug("Raw LLM response for technical tasks:")
        logger.debug("-" * 80)
        logger.debug(response)
        logger.debug("-" * 80)
        
        # Parse and process technical tasks
        parsed_tasks = TechnicalTaskParser.parse_from_response(response)
        for task_dict in parsed_tasks:
            try:
                # Generate additional components
                research_summary = await self._generate_research_summary(task_dict)
                code_blocks = await self._generate_code_examples(task_dict)
                scenarios = await self._generate_gherkin_scenarios(task_dict)
                
                # Create TechnicalTask model
                task = TechnicalTask(
                    **task_dict,
                    research_summary=research_summary,
                    code_blocks=code_blocks,
                    scenarios=scenarios
                )
                
                # Add to tracking systems
                task_tracker.add_technical_task(task.dict())
                task_id = proposed_tickets.add_high_level_task(task.dict())
                task.id = task_id
                
                # Add to tasks list
                tasks.append(task)
                
                # Log the task generation
                self.execution_log.log_llm_interaction(
                    f"Technical Task Generation - {task.title}",
                    prompt,
                    response,
                    {"technical_task": task.dict()}
                )
                
            except Exception as e:
                logger.error(f"Failed to process technical task {task_dict.get('title')}: {str(e)}")
                continue
        
        return tasks

    async def _generate_research_summary(self, task_context: Dict[str, Any]) -> ResearchSummary:
        """Generate research summary for a technical task"""
        prompt = TechnicalTaskPromptBuilder.build_technical_task_research_prompt(task_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        
        research_data = ResearchSummaryParser.parse(response)
        return ResearchSummary.parse_obj(research_data)

    async def _generate_code_examples(self, task_context: Dict[str, Any]) -> List[CodeBlock]:
        """Generate code examples for a technical task"""
        prompt = TechnicalTaskPromptBuilder.build_code_examples_prompt(task_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        
        code_blocks_data = CodeBlockParser.parse(response)
        return [CodeBlock.parse_obj(block) for block in code_blocks_data]

    async def _generate_gherkin_scenarios(self, task_context: Dict[str, Any]) -> List[GherkinScenario]:
        """Generate Gherkin scenarios for a technical task"""
        prompt = TechnicalTaskPromptBuilder.build_gherkin_scenarios_prompt(task_context)
        response = await self.llm.generate_content(prompt, temperature=0.2)
        
        scenarios_data = GherkinParser.parse(response)
        return [GherkinScenario.parse_obj(scenario) for scenario in scenarios_data] 