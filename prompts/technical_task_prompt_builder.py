from typing import Dict, Any, List

from .base_prompt_builder import BasePromptBuilder


class TechnicalTaskPromptBuilder(BasePromptBuilder):
    """Builder for technical task generation prompts"""

    @staticmethod
    def build_technical_tasks_prompt(user_stories: List[Dict[str, Any]], epic_analysis: Dict[str, Any]) -> str:
        """Build prompt for generating technical tasks"""
        # Format user stories properly
        formatted_stories = []
        for story in user_stories:
            description = story.get('description', {})
            formatted_desc = description.get('formatted', '') if isinstance(description, dict) else str(description)

            formatted_stories.append({
                "id": story.get('id', 'Unassigned'),
                "title": story.get('title', ''),
                "description": formatted_desc,
                "technical_domain": story.get('technical_domain', ''),
                "story_points": story.get('story_points', 3),
                "implementation_notes": story.get('implementation_notes', {})
            })

        return f"""
        Please create technical tasks based on these user stories and epic analysis. Focus on implementation details and technical requirements.

        IMPORTANT: You MUST return a JSON array of technical tasks following EXACTLY the structure specified below.

        User Stories:
        {BasePromptBuilder.format_dict_for_prompt({"stories": formatted_stories})}

        Epic Analysis:
        {BasePromptBuilder.format_dict_for_prompt(epic_analysis)}

        REQUIRED FORMAT - Each technical task in the array must have these exact fields:
        {{
            "title": "Technical Task - [Descriptive title]",
            "description": "Detailed technical description of what needs to be implemented",
            "technical_domain": "Primary technical domain this task belongs to",
            "complexity": "Low|Medium|High",
            "business_value": "Low|Medium|High",
            "story_points": "1|2|3|5|8|13",
            "required_skills": ["List of specific technical skills needed for implementation (e.g. React, Node.js, PostgreSQL)"],
            "suggested_assignee": "Role or specialty best suited for this task (e.g. Frontend Developer, Backend Developer, DevOps)",
            "dependencies": ["dependency1", "dependency2"],
            "implementation_approach": {{
                "architecture": "System architecture components and data flow",
                "apis": "Required APIs and services",
                "database": "Database changes and schema updates",
                "security": "Security considerations and requirements"
            }},
            "acceptance_criteria": ["criterion1", "criterion2"],
            "performance_impact": "Performance impact analysis",
            "scalability_considerations": "Scalability considerations",
            "monitoring_needs": "Monitoring and observability needs",
            "testing_requirements": "Testing requirements and approach"
        }}

        Guidelines:
        1. Each task should be focused on a specific technical implementation
        2. Include clear acceptance criteria and testing requirements
        3. Specify required skills based on the technical domain and implementation needs
        4. Suggest assignee based on the technical domain and required skills
        5. Consider dependencies between tasks and with user stories

        Return ONLY the JSON array, no additional text or explanation.
        """

    @staticmethod
    def build_technical_task_research_prompt(task_context: Dict[str, Any]) -> str:
        """Build prompt for generating technical task research summary"""
        return f"""
        Please conduct a thorough technical research analysis for this task. Focus on implementation approaches, potential challenges, and modern solutions.

        Task Context:
        {BasePromptBuilder.format_dict_for_prompt(task_context)}

        REQUIRED FORMAT - Return a JSON object with these exact fields:
        {{
            "pain_points": "Technical challenges and potential issues to address",
            "success_metrics": "Specific, measurable technical success criteria",
            "similar_implementations": "Examples of similar technical implementations and reference architectures",
            "modern_approaches": "Current (2024-2025) technical approaches, patterns, and best practices"
        }}

        Consider:
        1. Technical complexity and challenges
        2. Performance and scalability implications
        3. Security considerations
        4. Integration requirements
        5. Modern best practices and patterns

        Return ONLY the JSON object, no additional text or explanation.
        """

    @staticmethod
    def build_code_examples_prompt(task_context: Dict[str, Any]) -> str:
        """Build prompt for generating code examples"""
        return f"""
        Please provide example code snippets that demonstrate key technical implementation aspects of this task.

        Task Context:
        {BasePromptBuilder.format_dict_for_prompt(task_context)}

        REQUIRED FORMAT - Return a JSON array of code blocks, each with these exact fields:
        {{
            "language": "programming language",
            "description": "Brief description of what this code demonstrates",
            "code": "The actual code"
        }}

        Provide 2-3 relevant code examples that showcase:
        1. Core technical implementation
        2. Integration points and APIs
        3. Error handling and edge cases
        4. Performance considerations

        Return ONLY the JSON array, no additional text or explanation.
        """

    @staticmethod
    def build_gherkin_scenarios_prompt(task_context: Dict[str, Any]) -> str:
        """Build prompt for generating Gherkin scenarios"""
        return f"""
        Please create comprehensive Gherkin scenarios for testing this technical task. Include both happy path and edge cases.

        Task Context:
        {BasePromptBuilder.format_dict_for_prompt(task_context)}

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
        1. Core functionality testing
        2. Error conditions and edge cases
        3. Performance requirements
        4. Integration testing
        5. Security considerations

        Return ONLY the JSON array, no additional text or explanation.
        """

    @staticmethod
    def _format_user_stories(user_stories: List[Dict[str, Any]]) -> str:
        """Format user stories for inclusion in prompts"""
        formatted_stories = []
        for story in user_stories:
            formatted_stories.append(
                f"Story ID: {story.get('id', 'Unassigned')}\n"
                f"Title: {story['title']}\n"
                f"Description: {story['description']}\n"
                f"Story Points: {story.get('story_points', 3)}\n"
                f"Technical Domain: {story['technical_domain']}\n"
                f"Implementation Notes: {story.get('technical_notes', 'None provided')}\n"
            )
        return "\n".join(formatted_stories)
