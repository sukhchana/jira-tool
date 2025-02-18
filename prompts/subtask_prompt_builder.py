from typing import Dict, Any
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

        IMPORTANT: You MUST use EXACTLY the XML format specified below. DO NOT use markdown formatting or deviate from this structure.

        For each subtask, use this EXACT format:

        <subtask>
            <title>[Clear, specific title]</title>
            <description>[Detailed description]</description>
            <story_points>[1, 2, 3, 5, 8, or 13]</story_points>
            
            <technical_details>
                <required_skills>[List specific technologies/skills needed]</required_skills>
                <suggested_assignee>[Role/specialty best suited for this task]</suggested_assignee>
            </technical_details>

            <implementation_approach>
                <steps>
                    <step>[First implementation step]</step>
                    <step>[Second implementation step]</step>
                    <step>[Additional steps as needed]</step>
                </steps>
                <code_blocks>
                    <code language="[language]">
                        [Example code or pseudo-code showing key implementation steps]
                    </code>
                </code_blocks>
            </implementation_approach>

            <acceptance_criteria>
                <criterion>[First criterion]</criterion>
                <criterion>[Second criterion]</criterion>
                <criterion>[Additional criteria as needed]</criterion>
            </acceptance_criteria>

            <dependencies>
                <dependency>[First dependency]</dependency>
                <dependency>[Additional dependencies]</dependency>
            </dependencies>

            <testing>
                <unit_tests>[Unit testing approach]</unit_tests>
                <integration_tests>[Integration testing approach]</integration_tests>
                <edge_cases>[Key edge cases to test]</edge_cases>
            </testing>
        </subtask>

        CRITICAL FORMAT RULES:
        1. DO NOT use markdown formatting (**, _, etc.)
        2. DO NOT add any text outside the XML tags
        3. ALL content MUST be inside appropriate XML tags
        4. Each subtask MUST be wrapped in <subtask> tags
        5. ALL fields shown above are required
        6. Story points MUST be one of: 1, 2, 3, 5, 8, 13
        7. DO NOT add extra newlines or spaces between tags
        8. Write all subtasks consecutively without any separating text
        9. DO NOT add any prefixes, headers, or section titles
        10. Start your response with the first <subtask> tag and end with the last </subtask> tag

        Guidelines:
        1. Each subtask should be completable in 1-2 days
        2. Include clear acceptance criteria
        3. Specify required skills and estimated points
        4. Consider dependencies between subtasks
        5. Include example code or pseudo-code
        6. Provide testing guidance
        """ 