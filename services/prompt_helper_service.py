from typing import Dict, Any, Optional, List

class PromptHelperService:
    """Service for building and managing prompts for LLM interactions"""
    
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

    @staticmethod
    def build_epic_analysis_prompt(summary: str, description: str) -> str:
        """Build prompt for analyzing epic scope"""
        return f"""
        Please analyze this epic and provide a structured breakdown of its scope.

        Epic Summary: {summary}
        
        Epic Description:
        {description}

        First, provide a summary of your analysis:
        <summary>
        Total Technical Domains: [number]
        Total Core Requirements: [number]
        Total Dependencies: [number]
        Total Challenges: [number]
        </summary>

        Then provide the detailed analysis:
        <analysis>
        Main Objective: [Clear statement of the epic's primary goal]

        Stakeholders:
        [List key stakeholders]

        Core Requirements:
        [List main requirements]

        Technical Domains:
        [List technical areas involved]

        Dependencies:
        [List external dependencies]

        Challenges:
        [List potential challenges]
        </analysis>
        """

    @staticmethod
    def build_user_stories_prompt(epic_analysis: Dict[str, Any]) -> str:
        """Build prompt for generating user stories with Gherkin scenarios"""
        return f"""
        Please create user stories based on this epic analysis:

        {PromptHelperService._format_dict_for_prompt(epic_analysis)}

        First, provide a summary of planned stories:
        <summary>
        Total User Stories: [number]
        Key User Types: [list]
        Primary Value Streams: [list]
        </summary>

        Then, create 3-5 user stories that represent valuable features or capabilities.
        For each user story, provide both a description and Gherkin scenarios:

        <user_story>
        Task: User Story - [What the user can do]
        Description: As a [user type], I want to [action] so that [benefit]
        Technical Domain: [Primary technical area]
        Complexity: [Low/Medium/High]
        Business Value: [High/Medium/Low]
        Dependencies: [List any dependencies]

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
        </user_story>

        Remember:
        - Each story should have at least 2 scenarios (happy path and alternative/error path)
        - Use clear, specific Gherkin steps
        - Scenarios should be testable
        - Include relevant business context
        - Consider edge cases and error conditions
        - Use consistent terminology
        """

    @staticmethod
    def build_technical_tasks_prompt(user_stories: List[Dict[str, Any]], epic_analysis: Dict[str, Any]) -> str:
        """Build prompt for technical tasks generation"""
        return f"""
        Please create technical tasks needed to implement these user stories:

        User Stories:
        {PromptHelperService._format_user_stories(user_stories)}

        Technical Context:
        {PromptHelperService._format_epic_analysis(epic_analysis)}

        First, provide an implementation strategy:
        <strategy>
        Total Technical Tasks: [number]
        Key Technical Components: [list]
        Implementation Approach: [brief explanation]
        </strategy>

        Then, for each user story, create the necessary technical tasks using EXACTLY this format:

        <technical_task>
        **Task:** Technical Task - [What needs to be built]
        **Description:** [Technical implementation details]
        **Technical Domain:** [Specific technical area]
        **Complexity:** [Low/Medium/High]
        **Dependencies:** [Related user story or other tasks]
        **Implementation Notes:** [Key technical considerations]
        </technical_task>

        Important Formatting Requirements:
        1. Each task MUST be wrapped in <technical_task> tags
        2. Each field MUST be prefixed with double asterisks and colon (e.g., **Task:**)
        3. Each field MUST be on a new line
        4. Fields MUST appear in the exact order shown above
        5. All fields are required
        6. Use clear, specific titles for tasks
        7. Separate multiple dependencies with commas

        Requirements:
        - Each user story should have 1-2 technical tasks
        - Tasks should be specific and implementable
        - No task should take more than 3 days
        - Include both frontend and backend work where relevant
        - Consider infrastructure and testing needs
        - Break down complex tasks into smaller, manageable pieces
        """

    @staticmethod
    def build_subtasks_prompt(task: Dict[str, Any], epic_details: Dict[str, Any]) -> str:
        """Build prompt for breaking down tasks into subtasks"""
        return f"""
        Break down the following high-level task into detailed subtasks:

        Parent Task: {task['name']}
        Description: {task['description']}
        Technical Domain: {task['technical_domain']}
        Epic Context: {epic_details['summary']}

        First, provide a breakdown summary:
        <summary>
        Total Subtasks: [number]
        Estimated Total Story Points: [number]
        Required Skills: [comma-separated list]
        </summary>

        Then, for each subtask, provide ALL of the following details in this format:

        <subtask>
        Title: [Clear, specific title]
        Description: [Detailed technical description]
        Acceptance Criteria: [Clear, testable criteria]
        Story Points: [1-5]
        Required Skills: [Comma-separated list of required skills]
        Dependencies: [Comma-separated list of dependencies]
        Suggested Assignee: [Role/Specialty]
        </subtask>

        Requirements:
        - Each subtask MUST have ALL the fields listed above
        - Each subtask should be completable within 1-2 days
        - Include clear acceptance criteria
        - Specify technical requirements
        - Consider testing needs
        - Story points should be between 1-5
        - Titles should be clear and specific
        """

    @staticmethod
    def _format_dict_for_prompt(d: Dict[str, Any]) -> str:
        """Format a dictionary for use in prompts"""
        result = []
        for key, value in d.items():
            formatted_key = key.replace("_", " ").title()
            if isinstance(value, list):
                result.append(f"{formatted_key}:")
                result.extend([f"- {item}" for item in value])
            else:
                result.append(f"{formatted_key}: {value}")
        return "\n".join(result)

    @staticmethod
    def _format_user_stories(user_stories: List[Dict[str, Any]]) -> str:
        """Format user stories for use in prompts"""
        formatted = []
        for story in user_stories:
            formatted.append(f"Story: {story['name']}")
            formatted.append(f"Description: {story['description']}")
            formatted.append(f"Technical Domain: {story['technical_domain']}")
            formatted.append("")
        return "\n".join(formatted)

    @staticmethod
    def _format_epic_analysis(epic_analysis: Dict[str, Any]) -> str:
        """Format epic analysis for use in prompts"""
        formatted = []
        if "technical_domains" in epic_analysis:
            formatted.append("Technical Domains:")
            formatted.extend([f"- {domain}" for domain in epic_analysis["technical_domains"]])
            formatted.append("")
        if "core_requirements" in epic_analysis:
            formatted.append("Core Requirements:")
            formatted.extend([f"- {req}" for req in epic_analysis["core_requirements"]])
        return "\n".join(formatted)

    def build_enhanced_tasks_prompt(
        self,
        epic_analysis: Dict[str, Any],
        epic_description: str,
        retry_reason: str
    ) -> str:
        """Build an enhanced prompt for retry attempts"""
        return f"""
{retry_reason}

Original Epic Description:
{epic_description}

Analysis Summary:
Main Objective: {epic_analysis.get('main_objective', 'Not specified')}
Technical Domains: {', '.join(epic_analysis.get('technical_domains', []))}
Core Requirements: {', '.join(epic_analysis.get('core_requirements', []))}

First, provide a breakdown plan:
<plan>
Total User Stories Planned: [number]
Total Technical Tasks Planned: [number]
Primary Technical Domains: [list]
</plan>

Then create user stories:
<user_story>
Task: User Story - [Capability Name]
Description: As a [user type], I want to [action] so that [benefit]
Technical Domain: [Area of implementation]
Complexity: [Low/Medium/High]
Dependencies: [Prerequisites]
</user_story>

Then create technical tasks:
<technical_task>
Task: Technical Task - [Implementation Detail]
Description: [Specific technical work needed]
Technical Domain: [Backend/Frontend/Database/etc.]
Complexity: [Low/Medium/High]
Dependencies: [Related user story]
</technical_task>

Requirements:
1. Minimum 2-3 user stories
2. Each user story should have 1-2 technical tasks
3. No task should be larger than 3 days
4. Include both frontend and backend considerations
5. Consider setup/infrastructure needs
"""

    def build_forced_breakdown_prompt(
        self,
        epic_summary: str,
        epic_description: str,
        epic_analysis: Dict[str, Any]
    ) -> str:
        """Build a final prompt that forces a breakdown by suggesting structure"""
        return f"""
Let's systematically break down this epic: "{epic_summary}"

Original Description:
{epic_description}

Technical Domains: {', '.join(epic_analysis.get('technical_domains', []))}

First, provide your breakdown strategy:
<strategy>
Total Planned Stories: [number]
Total Planned Technical Tasks: [number]
Breakdown Approach: [Brief explanation]
</strategy>

Please create the following breakdown:

1. Core User Stories (minimum 2):
<user_story>
Task: User Story - [Feature Name]
Description: As a [user], I want to [action] so that [benefit]
Technical Domain: [Area]
Complexity: [Low/Medium/High]
Dependencies: [Any prerequisites]
</user_story>

2. Technical Foundation (minimum 1):
<technical_task>
Task: Technical Task - [Setup/Infrastructure need]
Description: [Technical implementation details]
Technical Domain: [Specific area]
Complexity: [Low/Medium/High]
Dependencies: [Prerequisites]
</technical_task>

3. Implementation Tasks (minimum 2 per user story):
<technical_task>
Task: Technical Task - [Implementation detail]
Description: [Specific work needed]
Technical Domain: [Area]
Complexity: [Low/Medium/High]
Dependencies: [Related user story]
</technical_task>

4. Quality & Delivery (minimum 1):
<technical_task>
Task: Technical Task - [Testing/Documentation need]
Description: [Specific requirements]
Technical Domain: [QA/Documentation]
Complexity: [Low/Medium/High]
Dependencies: [Related stories/tasks]
</technical_task>

Finally, provide a completion summary:
<summary>
Total User Stories Created: [number]
Total Technical Tasks Created: [number]
Estimated Timeline: [weeks]
Key Technical Domains Covered: [list]
</summary>
""" 