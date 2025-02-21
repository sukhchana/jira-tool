from typing import Dict, Any, List
from .base_prompt_builder import BasePromptBuilder

class SubtaskPromptBuilder(BasePromptBuilder):
    """Builder for subtask breakdown prompts"""
    
    @staticmethod
    def build_subtasks_prompt(task: Dict[str, Any], epic_details: Dict[str, Any]) -> str:
        """Build prompt for breaking down tasks into subtasks"""
        return f"""
        Please break down this task into specific, actionable subtasks.
        Consider the epic context and task details when creating subtasks.

        Epic Context:
        {BasePromptBuilder.format_dict_for_prompt(epic_details)}

        Task to Break Down:
        {BasePromptBuilder.format_dict_for_prompt(task)}

        IMPORTANT: You MUST return a JSON array of subtasks following EXACTLY the structure specified below.

        REQUIRED FORMAT - Each subtask in the array must have these exact fields:
        {{
            "title": "Subtask - [Descriptive title]",
            "description": "Detailed description of what needs to be implemented",
            "technical_domain": "Primary technical domain this subtask belongs to",
            "complexity": "Low|Medium|High",
            "business_value": "Low|Medium|High",
            "story_points": "1|2|3|5|8|13",
            "required_skills": ["List of specific technical skills needed for implementation (e.g. React, Node.js, PostgreSQL)"],
            "suggested_assignee": "Role or specialty best suited for this subtask (e.g. Frontend Developer, Backend Developer, DevOps)",
            "dependencies": ["dependency1", "dependency2"],
            "acceptance_criteria": ["criterion1", "criterion2"],
            "parent_id": "ID of the parent task"
        }}

        Guidelines:
        1. Each subtask should be completable in 1-2 days
        2. Include clear acceptance criteria
        3. Specify required skills based on the technical implementation needs
        4. Suggest assignee based on the technical domain and required skills
        5. Consider dependencies between subtasks
        6. Ensure the parent_id matches the task's ID

        Return ONLY the JSON array, no additional text or explanation.
        """

    @staticmethod
    def build_implementation_approach_prompt(subtask_context: Dict[str, Any]) -> str:
        """Build prompt for generating implementation approach details"""
        return f"""
        Please provide a detailed implementation approach for this subtask.

        Subtask Context:
        {BasePromptBuilder.format_dict_for_prompt(subtask_context)}

        REQUIRED FORMAT - Return a JSON object with these exact fields:
        {{
            "architecture": "System architecture components and data flow",
            "apis": "Required APIs and services",
            "database": "Database changes and schema updates",
            "security": "Security considerations and requirements",
            "implementation_steps": [
                "Step 1: Detailed implementation step",
                "Step 2: Next implementation step"
            ],
            "potential_challenges": [
                "Challenge 1: Description and mitigation",
                "Challenge 2: Description and mitigation"
            ]
        }}

        Return ONLY the JSON object, no additional text or explanation.
        """

    @staticmethod
    def build_code_examples_prompt(subtask_context: Dict[str, Any]) -> str:
        """Build prompt for generating code examples"""
        return f"""
        Please provide example code snippets that demonstrate key implementation aspects of this subtask.

        Subtask Context:
        {BasePromptBuilder.format_dict_for_prompt(subtask_context)}

        REQUIRED FORMAT - Return a JSON array of code blocks, each with these exact fields:
        {{
            "language": "programming language",
            "description": "Brief description of what this code demonstrates",
            "code": "The actual code",
            "test_cases": [
                {{
                    "description": "Test case description",
                    "code": "Test code"
                }}
            ]
        }}

        Provide 2-3 relevant code examples that showcase:
        1. Core implementation
        2. Integration points
        3. Error handling and edge cases
        4. Unit test examples

        Return ONLY the JSON array, no additional text or explanation.
        """

    @staticmethod
    def build_testing_plan_prompt(subtask_context: Dict[str, Any]) -> str:
        """Build prompt for generating testing plan"""
        return f"""
        Please create a comprehensive testing plan for this subtask.

        Subtask Context:
        {BasePromptBuilder.format_dict_for_prompt(subtask_context)}

        REQUIRED FORMAT - Return a JSON object with these exact fields:
        {{
            "unit_tests": [
                "Test scenario 1: Description",
                "Test scenario 2: Description"
            ],
            "integration_tests": [
                "Test scenario 1: Description",
                "Test scenario 2: Description"
            ],
            "edge_cases": [
                "Edge case 1: Description and test approach",
                "Edge case 2: Description and test approach"
            ],
            "performance_tests": [
                "Performance scenario 1: Description and metrics",
                "Performance scenario 2: Description and metrics"
            ],
            "test_data_requirements": [
                "Data requirement 1: Description",
                "Data requirement 2: Description"
            ]
        }}

        Return ONLY the JSON object, no additional text or explanation.
        """

    @staticmethod
    def build_research_summary_prompt(subtask_context: Dict[str, Any]) -> str:
        """Build prompt for generating research summary"""
        return f"""
        Please conduct a thorough technical research analysis for this subtask.

        Subtask Context:
        {BasePromptBuilder.format_dict_for_prompt(subtask_context)}

        REQUIRED FORMAT - Return a JSON object with these exact fields:
        {{
            "pain_points": "Technical challenges and potential issues to address",
            "success_metrics": "Specific, measurable technical success criteria",
            "similar_implementations": "Examples of similar technical implementations and reference architectures",
            "modern_approaches": "Current (2024-2025) technical approaches, patterns, and best practices",
            "performance_considerations": "Performance impact and optimization opportunities",
            "security_implications": "Security considerations and best practices",
            "maintenance_aspects": "Long-term maintenance and supportability considerations"
        }}

        Return ONLY the JSON object, no additional text or explanation.
        """ 