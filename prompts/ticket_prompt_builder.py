from typing import Dict, Any, Optional

from .base_prompt_builder import BasePromptBuilder


class TicketPromptBuilder(BasePromptBuilder):
    """Builder for individual ticket prompts"""

    @staticmethod
    def build_ticket_prompt(
            context: str,
            requirements: Optional[str] = None,
            additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for ticket description generation"""
        prompt_parts = [
            "Please create a well-structured JIRA ticket with the following information:\n\n",
            f"Context: {context}\n"
        ]

        if requirements:
            prompt_parts.append(f"Requirements: {requirements}\n")

        if additional_info:
            prompt_parts.append("Additional Information:\n")
            for key, value in additional_info.items():
                prompt_parts.append(f"- {key}: {value}\n")

        prompt_parts.append("""
Please format the response using EXACTLY this structure:

<ticket>
Title: [Clear, concise title]
Description: [Detailed description of the work required]

Technical Domain: [Primary technical area]
Required Skills: [Comma-separated list of key technical skills needed]
Story Points: [1-5]
Suggested Assignee: [Role/specialty of ideal assignee]
Complexity: [Low/Medium/High]

Acceptance Criteria:
[List of specific, testable criteria]

Scenarios:
Scenario: [Happy path scenario name]
Given [initial context]
When [action is taken]
Then [expected outcome]
And [additional outcome if needed]

Scenario: [Alternative/error path name]
Given [initial context]
When [action is taken]
Then [expected outcome]

Technical Notes:
[Implementation details, architectural considerations, etc.]
</ticket>

Requirements:
- Title should be clear and actionable
- Description should provide comprehensive context
- Include at least 2 Gherkin scenarios (happy path and error case)
- Story points should reflect complexity (1-5 scale)
- Required skills should be specific technologies/frameworks
- Technical notes should include implementation guidance
""")

        return "".join(prompt_parts)

    @staticmethod
    def build_complexity_prompt(ticket_description: str) -> str:
        """Build prompt for ticket complexity analysis"""
        return f"""
        Please analyze the following JIRA ticket description and provide:
        1. Estimated complexity (Low/Medium/High)
        2. Estimated story points (1-8)
        3. Key technical considerations
        4. Potential risks
        
        Ticket Description:
        {ticket_description}
        """
