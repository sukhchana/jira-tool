from typing import Dict, Any

from .base_prompt_builder import BasePromptBuilder


class UserStoryPromptBuilder(BasePromptBuilder):
    """Builder for user story generation prompts"""

    @staticmethod
    def build_user_stories_prompt(epic_analysis: Dict[str, Any]) -> str:
        """Build prompt for generating user stories with Gherkin scenarios"""
        return f"""
        Please create 3-5 user stories based on this epic analysis. For each story, focus on clear user value and technical feasibility.

        IMPORTANT: You MUST return a JSON array of user stories following EXACTLY the structure specified below.

        Epic Analysis:
        {BasePromptBuilder.format_dict_for_prompt(epic_analysis)}

        REQUIRED FORMAT - Each user story in the array must have these exact fields:
        {{
            "title": "User Story - [Descriptive title]",
            "description": {{
                "role": "The user role/persona",
                "goal": "What the user wants to accomplish",
                "benefit": "The value/benefit to the user",
                "formatted": "As a [role], I want [goal], so that [benefit]"
            }},
            "technical_domain": "Primary technical domain this story belongs to",
            "complexity": "Low|Medium|High",
            "business_value": "Low|Medium|High",
            "story_points": "1|2|3|5|8|13",
            "required_skills": ["List of specific technical skills needed for implementation (e.g. React, Node.js, PostgreSQL)"],
            "suggested_assignee": "Role or specialty best suited for this story (e.g. Frontend Developer, Backend Developer, Full Stack)",
            "dependencies": ["dependency1", "dependency2"],
            "acceptance_criteria": ["criterion1", "criterion2"],
            "implementation_notes": {{
                "technical_considerations": "Key technical aspects to consider",
                "integration_points": "Integration requirements",
                "accessibility": "Accessibility requirements"
            }}
        }}

        Guidelines:
        1. Each story should be focused on a single user goal
        2. Include clear acceptance criteria
        3. Specify required skills based on technical implementation needs
        4. Suggest assignee based on the primary technical domain and skills
        5. Consider dependencies between stories

        Return ONLY the JSON array, no additional text or explanation.
        """

    @staticmethod
    def build_research_prompt(story_context: Dict[str, Any]) -> str:
        """Build prompt for generating user story research summary"""
        return f"""
        Please conduct a thorough research analysis for this user story. Focus on current pain points, success metrics, similar implementations, and modern approaches.

        User Story Context:
        {BasePromptBuilder.format_dict_for_prompt(story_context)}

        REQUIRED FORMAT - Return a JSON object with these exact fields:
        {{
            "pain_points": "Detailed analysis of current pain points this story addresses",
            "success_metrics": "Specific, measurable metrics to evaluate the success of this story",
            "similar_implementations": "Examples of similar implementations, tools, or references that can guide this implementation",
            "modern_approaches": "Current (2024-2025) best practices, patterns, and modern approaches relevant to this story"
        }}

        Return ONLY the JSON object, no additional text or explanation.
        """

    @staticmethod
    def build_code_examples_prompt(story_context: Dict[str, Any]) -> str:
        """Build prompt for generating code examples"""
        return f"""
        Please provide example code snippets that demonstrate key implementation aspects of this user story. Include modern best practices and patterns.

        User Story Context:
        {BasePromptBuilder.format_dict_for_prompt(story_context)}

        REQUIRED FORMAT - Return a JSON array of code blocks, each with these exact fields:
        {{
            "language": "programming language",
            "description": "Brief description of what this code demonstrates",
            "code": "The actual code"
        }}

        Provide 2-3 relevant code examples that showcase:
        1. Core functionality implementation
        2. Integration points
        3. Error handling and edge cases

        Return ONLY the JSON array, no additional text or explanation.
        """

    @staticmethod
    def build_gherkin_scenarios_prompt(story_context: Dict[str, Any]) -> str:
        """Build prompt for generating Gherkin scenarios"""
        return f"""
        Please create comprehensive Gherkin scenarios for acceptance testing of this user story. Include both happy path and edge cases.

        User Story Context:
        {BasePromptBuilder.format_dict_for_prompt(story_context)}

        REQUIRED FORMAT - Return a JSON array of scenarios, each with these exact fields:
        {{
            "name": "Descriptive scenario name",
            "steps": [
                {{
                    "keyword": "Given|When|Then|And",
                    "text": "Step description"
                }}
            ]
        }}

        Create 3-5 scenarios that cover:
        1. Happy path flow
        2. Error conditions and edge cases
        3. Performance requirements
        4. Security considerations
        5. Accessibility requirements

        Return ONLY the JSON array, no additional text or explanation.
        """
