from typing import Dict, Any

from loguru import logger

from llm.vertexllm import VertexLLM
from models.analysis_info import AnalysisInfo
from models.complexity_analysis import ComplexityAnalysis
from models.ticket_description import TicketDescription
from parsers import TicketDescriptionParser, EpicAnalysisParser, ComplexityAnalysisParser
from prompts.epic_prompt_builder import EpicPromptBuilder
from prompts.ticket_prompt_builder import TicketPromptBuilder
from services.execution_log_service import ExecutionLogService
from services.format_fixer_service import FormatFixerService


class EpicAnalyzer:
    """Service responsible for analyzing epics and breaking them down"""

    def __init__(self, execution_log: ExecutionLogService):
        self.llm = VertexLLM()
        self.format_fixer = FormatFixerService(llm_service=self.llm)
        self.execution_log = execution_log

    async def analyze_epic(self, summary: str, description: str) -> AnalysisInfo:
        """
        Analyze an epic's scope and requirements.
        
        Args:
            summary: Epic summary/title
            description: Epic description
            
        Returns:
            AnalysisInfo containing structured analysis of the epic
        """
        try:
            # Generate epic analysis prompt and get LLM response
            prompt = EpicPromptBuilder.build_epic_analysis_prompt(summary, description)
            response = await self.llm.generate_content(
                prompt,
                temperature=0.2,
                top_p=0.8,
                top_k=40
            )

            # Debug log the response
            logger.debug("Raw LLM response for epic analysis:")
            logger.debug("-" * 80)
            logger.debug(response)
            logger.debug("-" * 80)

            # Parse the response
            analysis_dict = await EpicAnalysisParser.parse_with_format_fixing(response, self.format_fixer)

            # Convert to AnalysisInfo model
            epic_analysis = AnalysisInfo(
                main_objective=analysis_dict["main_objective"],
                technical_domains=analysis_dict.get("technical_domains", []),
                core_requirements=analysis_dict.get("core_requirements", []),
                stakeholders=analysis_dict.get("stakeholders", [])
            )

            # Log the analysis
            self.execution_log.log_llm_interaction(
                "Epic Analysis",
                prompt,
                response,
                epic_analysis.model_dump()
            )

            return epic_analysis

        except Exception as e:
            logger.error(f"Failed to analyze epic: {str(e)}")
            logger.error(f"Summary: {summary}")
            logger.error(f"Description: {description}")
            # Return a default AnalysisInfo in case of error
            return AnalysisInfo(
                main_objective="Error analyzing epic",
                technical_domains=[],
                core_requirements=[],
                stakeholders=[]
            )


    async def analyze_complexity(self, epic_summary: str, epic_description: str) -> ComplexityAnalysis:
        """
        Analyze the complexity of an epic and estimate effort.
        
        Args:
            epic_summary: The summary/title of the epic
            epic_description: The description of the epic
            
        Returns:
            ComplexityAnalysis containing structured analysis and metrics
        """
        try:
            prompt = EpicPromptBuilder.build_complexity_prompt(epic_summary, epic_description)
            response = await self.llm.generate_content(
                prompt,
                temperature=0.1,
                top_p=0.8,
                top_k=40
            )

            # Parse the response into structured format
            analysis_data = ComplexityAnalysisParser.parse(response)
            
            # Create and return ComplexityAnalysis model
            return ComplexityAnalysis(
                analysis=analysis_data["analysis"],
                raw_response=response,
                story_points=analysis_data.get("story_points", 0),
                complexity_level=analysis_data.get("complexity_level", "Medium"),
                effort_estimate=analysis_data.get("effort_estimate", ""),
                technical_factors=analysis_data.get("technical_factors", []),
                risk_factors=analysis_data.get("risk_factors", [])
            )

        except Exception as e:
            logger.error(f"Failed to analyze epic complexity: {str(e)}")
            logger.error(f"Epic summary: {epic_summary}")
            logger.error(f"Epic description: {epic_description}")
            raise

    async def generate_ticket_description(
            self,
            context: str,
            requirements: str = None,
            additional_info: Dict[str, Any] = None
    ) -> TicketDescription:
        """
        Generate a structured ticket description using LLM.
        
        Args:
            context: Main context/purpose of the ticket
            requirements: Optional specific requirements
            additional_info: Optional additional context
            
        Returns:
            TicketDescription model containing structured ticket description
        """
        try:
            prompt = TicketPromptBuilder.build_ticket_prompt(context, requirements, additional_info)
            response = await self.llm.generate_content(
                prompt,
                temperature=0.2,
                top_p=0.8,
                top_k=40
            )
            return TicketDescriptionParser.parse(response)

        except Exception as e:
            logger.error(f"Failed to generate ticket description: {str(e)}")
            logger.error(f"Context: {context}")
            raise
