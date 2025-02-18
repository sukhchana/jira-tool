from typing import Dict, Any, List
from loguru import logger
from prompts.epic_prompt_builder import EpicPromptBuilder
from prompts.ticket_prompt_builder import TicketPromptBuilder
from services.execution_log_service import ExecutionLogService
from llm.vertexllm import VertexLLM
from parsers import TicketDescriptionParser, EpicAnalysisParser
from services.format_fixer_service import FormatFixerService
import json

class EpicAnalyzer:
    """Service responsible for analyzing epics and breaking them down"""
    
    def __init__(self, execution_log: ExecutionLogService):
        self.llm = VertexLLM()
        self.format_fixer = FormatFixerService(llm_service=self.llm)
        self.execution_log = execution_log

    async def analyze_epic(self, summary: str, description: str) -> Dict[str, Any]:
        """
        Analyze an epic's scope and requirements.
        
        Args:
            summary: Epic summary/title
            description: Epic description
            
        Returns:
            Structured analysis of the epic
        """
        try:
            # Generate epic analysis prompt and get LLM response
            prompt = EpicPromptBuilder.build_epic_analysis_prompt(summary, description)
            response = await self.llm.generate_content(prompt, temperature=0.2)
            
            # Debug log the response
            logger.debug("Raw LLM response for epic analysis:")
            logger.debug("-" * 80)
            logger.debug(response)
            logger.debug("-" * 80)
            
            # Parse the response
            epic_analysis = await EpicAnalysisParser.parse_with_format_fixing(response, self.format_fixer)
            
            # Log the analysis
            self.execution_log.log_llm_interaction(
                "Epic Analysis",
                prompt,
                response,
                epic_analysis
            )
            
            return epic_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze epic: {str(e)}")
            logger.error(f"Summary: {summary}")
            logger.error(f"Description: {description}")
            return {
                "main_objective": "Error analyzing epic",
                "stakeholders": [],
                "core_requirements": [],
                "technical_domains": [],
                "dependencies": [],
                "challenges": []
            }

    def parse_ticket_description(self, response: str) -> Dict[str, Any]:
        """Parse ticket description from LLM response"""
        return TicketDescriptionParser.parse(response)

    async def analyze_complexity(self, ticket_description: str) -> Dict[str, Any]:
        """
        Analyze the complexity of a ticket and estimate effort.
        
        Args:
            ticket_description: The description of the ticket to analyze
            
        Returns:
            Dict containing complexity analysis and raw response
        """
        try:
            prompt = EpicPromptBuilder.build_complexity_prompt(ticket_description)
            response = await self.llm.generate_content(
                prompt,
                max_output_tokens=512,
                temperature=0.1
            )
            
            return {
                "analysis": response,
                "raw_response": response
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze ticket complexity: {str(e)}")
            logger.error(f"Ticket description: {ticket_description}")
            raise
    
    async def generate_ticket_description(
        self,
        context: str,
        requirements: str = None,
        additional_info: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """
        Generate a structured ticket description using LLM.
        
        Args:
            context: Main context/purpose of the ticket
            requirements: Optional specific requirements
            additional_info: Optional additional context
            
        Returns:
            Dict containing structured ticket description
        """
        try:
            prompt = TicketPromptBuilder.build_ticket_prompt(context, requirements, additional_info)
            response = await self.llm.generate_content(prompt)
            return self.parse_ticket_description(response)
            
        except Exception as e:
            logger.error(f"Failed to generate ticket description: {str(e)}")
            logger.error(f"Context: {context}")
            raise 