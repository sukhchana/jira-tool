from typing import Dict, Any, Optional
from loguru import logger
from prompts.epic_prompt_builder import EpicPromptBuilder
from prompts.user_story_prompt_builder import UserStoryPromptBuilder
from prompts.technical_task_prompt_builder import TechnicalTaskPromptBuilder
from parsers import EpicAnalysisParser, UserStoryParser, TechnicalTaskParser

class FormatFixerService:
    """Service for fixing formatting issues in LLM responses"""
    
    def __init__(self, llm_service):
        """Initialize with LLM service for reformatting"""
        self.llm_service = llm_service

    def build_format_fixer_prompt(self, content: str, content_type: str, parsing_error: Optional[str] = None) -> str:
        """
        Build a prompt to fix formatting issues in LLM responses.
        
        Args:
            content: The original LLM response that needs reformatting
            content_type: Type of content ('epic_analysis', 'user_story', or 'technical_task')
            parsing_error: Optional error message from the parser to help guide the correction
            
        Returns:
            A prompt asking the LLM to reformat the content into proper XML format
        """
        base_prompt = f"""
        Please reformat the following content into a properly structured XML format. The content appears to be a {content_type}.
        
        CRITICAL FORMATTING RULES:
        1. ALL content MUST be wrapped in appropriate XML tags
        2. DO NOT add any text or explanations outside of XML tags
        3. DO NOT use markdown formatting (**, _, etc.)
        4. Use consistent indentation and spacing
        5. Ensure all tags are properly closed
        6. Use descriptive tag names that match our expected format
        7. Preserve all original content and meaning
        8. Remove any non-XML formatting or decorations
        9. Ensure special characters are properly escaped
        10. Maintain hierarchical structure of the data

        Original content to reformat:
        {content}
        """

        if parsing_error:
            base_prompt += f"""
            
            The previous attempt resulted in the following error:
            {parsing_error}
            
            Please ensure your reformatting addresses this specific issue.
            """

        # Add expected format based on content type
        if content_type == "epic_analysis":
            base_prompt += """
            Expected format:
            <epic_analysis>
                <main_objective>[Clear statement of the epic's primary goal]</main_objective>
                <stakeholders>
                    <stakeholder>[First stakeholder]</stakeholder>
                    <stakeholder>[Second stakeholder]</stakeholder>
                </stakeholders>
                <core_requirements>
                    <requirement>[First requirement]</requirement>
                    <requirement>[Second requirement]</requirement>
                </core_requirements>
                <technical_domains>
                    <domain>[First domain with best practices]</domain>
                    <domain>[Second domain with best practices]</domain>
                </technical_domains>
                <dependencies>
                    <dependency>[First dependency]</dependency>
                    <dependency>[Second dependency]</dependency>
                </dependencies>
                <challenges>
                    <challenge>[First challenge]</challenge>
                    <challenge>[Second challenge]</challenge>
                </challenges>
            </epic_analysis>
            """
        elif content_type == "user_story":
            base_prompt += """
            Expected format:
            <user_story>
                <title>User Story - [Descriptive title]</title>
                <description>
                    <role>[The user role/persona]</role>
                    <goal>[What the user wants to accomplish]</goal>
                    <benefit>[The value/benefit to the user]</benefit>
                    <formatted>As a [role], I want [goal], so that [benefit]</formatted>
                </description>
                <technical_domain>[Primary technical domain]</technical_domain>
                <complexity>Low|Medium|High</complexity>
                <business_value>Low|Medium|High</business_value>
                <story_points>1|2|3|5|8|13</story_points>
                <required_skills>
                    <skill>[First required skill]</skill>
                    <skill>[Second required skill]</skill>
                </required_skills>
                <suggested_assignee>[Role best suited for this story]</suggested_assignee>
                <dependencies>
                    <dependency>[First dependency]</dependency>
                    <dependency>[Second dependency]</dependency>
                </dependencies>
                <acceptance_criteria>
                    <criterion>[First criterion]</criterion>
                    <criterion>[Second criterion]</criterion>
                </acceptance_criteria>
                <implementation_notes>
                    <technical_considerations>[Key technical aspects]</technical_considerations>
                    <integration_points>[Integration requirements]</integration_points>
                    <accessibility>[Accessibility requirements]</accessibility>
                </implementation_notes>
            </user_story>
            """
        elif content_type == "technical_task":
            base_prompt += """
            Expected format:
            <technical_task>
                <title>Technical Task - [Descriptive title]</title>
                <description>[Detailed technical description]</description>
                <technical_domain>[Primary technical domain]</technical_domain>
                <complexity>Low|Medium|High</complexity>
                <business_value>Low|Medium|High</business_value>
                <story_points>1|2|3|5|8|13</story_points>
                <required_skills>
                    <skill>[First required skill]</skill>
                    <skill>[Second required skill]</skill>
                </required_skills>
                <suggested_assignee>[Role best suited for this task]</suggested_assignee>
                <dependencies>
                    <dependency>[First dependency]</dependency>
                    <dependency>[Second dependency]</dependency>
                </dependencies>
                <implementation_approach>
                    <architecture>[System architecture components and data flow]</architecture>
                    <apis>[Required APIs and services]</apis>
                    <database>[Database changes and schema updates]</database>
                    <security>[Security considerations and requirements]</security>
                </implementation_approach>
                <acceptance_criteria>
                    <criterion>[First criterion]</criterion>
                    <criterion>[Second criterion]</criterion>
                </acceptance_criteria>
                <performance_impact>[Performance impact analysis]</performance_impact>
                <scalability_considerations>[Scalability considerations]</scalability_considerations>
                <monitoring_needs>[Monitoring and observability needs]</monitoring_needs>
                <testing_requirements>[Testing requirements and approach]</testing_requirements>
            </technical_task>
            """

        base_prompt += """
        
        Please reformat the content above into this exact XML structure, preserving all the original information but ensuring it follows proper XML formatting rules.
        Start your response with the appropriate opening XML tag and end with its closing tag.
        DO NOT add any additional text, explanations, or formatting outside the XML tags.
        """

        return base_prompt

    async def fix_format(self, content: str, content_type: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Attempt to fix formatting issues in LLM responses by requesting reformatting.
        
        Args:
            content: The original LLM response that needs reformatting
            content_type: Type of content ('epic_analysis', 'user_story', or 'technical_task')
            max_retries: Maximum number of retries for reformatting
            
        Returns:
            Parsed content if successful, None if all retries fail
        """
        parser = self._get_parser(content_type)
        if not parser:
            logger.error(f"Unknown content type: {content_type}")
            return None

        current_content = content
        parsing_error = None

        for attempt in range(max_retries):
            try:
                # Try parsing the current content
                result = parser.parse(current_content)
                if self._is_valid_result(result, content_type):
                    logger.info(f"Successfully parsed {content_type} on attempt {attempt + 1}")
                    return result

            except Exception as e:
                parsing_error = str(e)
                logger.warning(f"Parsing failed on attempt {attempt + 1}: {parsing_error}")

            # Generate format fixing prompt
            prompt = self.build_format_fixer_prompt(
                current_content,
                content_type,
                parsing_error
            )

            try:
                # Get reformatted content from LLM
                reformatted_content = await self.llm_service.generate_content(prompt)
                if reformatted_content:
                    current_content = reformatted_content
                else:
                    logger.error("LLM returned empty response for format fixing")
                    break
            except Exception as e:
                logger.error(f"Failed to get reformatted content from LLM: {str(e)}")
                break

        logger.error(f"Failed to fix {content_type} format after {max_retries} attempts")
        return None

    def _get_parser(self, content_type: str):
        """Get the appropriate parser for the content type"""
        parsers = {
            "epic_analysis": EpicAnalysisParser,
            "user_story": UserStoryParser,
            "technical_task": TechnicalTaskParser
        }
        return parsers.get(content_type)

    def _is_valid_result(self, result: Dict[str, Any], content_type: str) -> bool:
        """Check if the parsed result is valid for the content type"""
        if not result:
            return False

        required_fields = {
            "epic_analysis": ["main_objective", "stakeholders", "core_requirements"],
            "user_story": ["title", "description", "acceptance_criteria"],
            "technical_task": ["title", "description", "implementation_approach"]
        }

        fields = required_fields.get(content_type, [])
        return all(field in result for field in fields) 