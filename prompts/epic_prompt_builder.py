from typing import Dict, Any
from .base_prompt_builder import BasePromptBuilder

class EpicPromptBuilder(BasePromptBuilder):
    """Builder for epic analysis prompts"""
    
    @staticmethod
    def build_epic_analysis_prompt(summary: str, description: str) -> str:
        """Build prompt for analyzing epic scope"""
        return f"""
        Please analyze this epic and provide a structured breakdown of its scope.
        You have access to internet search - please use it to:
        1. Research current best practices and technologies relevant to this epic
        2. Identify potential technical challenges or limitations
        3. Find similar implementations or case studies
        4. Stay updated on latest industry standards and compliance requirements

        Epic Summary: {summary}
        
        Epic Description:
        {description}

        First, provide a summary of your analysis:
        <summary>
        <total_technical_domains>[number]</total_technical_domains>
        <total_core_requirements>[number]</total_core_requirements>
        <total_dependencies>[number]</total_dependencies>
        <total_challenges>[number]</total_challenges>
        <research_findings>[key insights from internet search]</research_findings>
        </summary>

        Then provide the detailed analysis:
        <analysis>
        <main_objective>
        [Clear statement of the epic's primary goal]
        </main_objective>

        <stakeholders>
        - [First stakeholder]
        - [Second stakeholder]
        </stakeholders>

        <core_requirements>
        - [First requirement]
        - [Second requirement]
        </core_requirements>

        <technical_domains>
        - [First domain with best practices]
        - [Second domain with best practices]
        </technical_domains>

        <dependencies>
        - [First dependency]
        - [Second dependency]
        </dependencies>

        <challenges>
        - [First challenge]
        - [Second challenge]
        </challenges>

        <industry_context>
        - [Industry standards]
        - [Best practices]
        - [Compliance requirements]
        </industry_context>
        </analysis>
        """
    
    @staticmethod
    def build_enhanced_tasks_prompt(
        epic_analysis: Dict[str, Any],
        epic_description: str,
        retry_reason: str
    ) -> str:
        """Build prompt for enhanced task generation after a retry"""
        return f"""
        Previous task generation attempt needs improvement. Please provide an enhanced breakdown
        considering the following feedback:

        Retry Reason: {retry_reason}

        Epic Description:
        {epic_description}

        Previous Analysis:
        {BasePromptBuilder.format_dict_for_prompt(epic_analysis)}

        Please provide a revised task breakdown that:
        1. Addresses the retry reason directly
        2. Ensures comprehensive coverage of all requirements
        3. Maintains clear dependencies and relationships
        4. Includes specific technical considerations
        5. Follows best practices for task granularity

        Format the response as:
        <enhanced_tasks>
        [List of tasks with clear rationale for each]
        </enhanced_tasks>
        """
    
    @staticmethod
    def build_forced_breakdown_prompt(
        epic_summary: str,
        epic_description: str,
        epic_analysis: Dict[str, Any]
    ) -> str:
        """Build prompt for forced breakdown when normal flow fails"""
        return f"""
        Please provide a simplified breakdown of this epic into basic tasks.
        Focus on creating a minimal viable set of tasks that:
        1. Cover core functionality
        2. Can be implemented independently
        3. Have clear, achievable goals

        Epic Summary: {epic_summary}

        Epic Description:
        {epic_description}

        Previous Analysis:
        {BasePromptBuilder.format_dict_for_prompt(epic_analysis)}

        Format each task as:
        <task>
        Title: [Clear title]
        Goal: [Specific objective]
        Implementation Steps: [Basic steps]
        Dependencies: [Minimal list]
        </task>
        """

    @staticmethod
    def build_task_generation_prompt(epic_analysis: Dict[str, Any]) -> str:
        """Build prompt for generating initial high-level tasks"""
        return f"""
        Based on the epic analysis, please generate a set of high-level tasks.
        
        Epic Analysis:
        {BasePromptBuilder.format_dict_for_prompt(epic_analysis)}
        
        Please provide both user stories and technical tasks in the following formats:

        For user stories:
        <user_story>
        Title: User Story - [What the user can do]
        Description: As a [user type], I want to [action] so that [benefit]
        Technical Domain: [Primary technical area]
        Dependencies: [Any prerequisites or related tasks]
        Complexity: [Low/Medium/High]
        Business Value: [High/Medium/Low]
        </user_story>

        For technical tasks:
        <technical_task>
        Title: Technical Task - [Clear and specific title]
        Description: [Detailed description of what needs to be done]
        Technical Domain: [Primary technical area - Frontend/Backend/Database/etc.]
        Dependencies: [Any prerequisites or related tasks]
        Complexity: [Low/Medium/High]
        Estimated Duration: [In days]
        </technical_task>
        
        Requirements:
        1. Tasks should be granular enough to be completed within 1-3 days
        2. Include both user stories and technical tasks
        3. Consider setup and infrastructure requirements
        4. Include testing and documentation tasks
        5. Ensure clear dependencies between tasks
        
        Format your response as:
        <tasks_summary>
        Total Tasks: [number]
        User Stories: [number]
        Technical Tasks: [number]
        Technical Domains Covered: [list]
        Estimated Total Duration: [in days]
        </tasks_summary>
        
        <tasks>
        [List of user stories and technical tasks in the formats specified above]
        </tasks>
        """ 