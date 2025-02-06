from typing import Dict, Any, Optional, List
from config.breakdown_config import BreakdownConfig

class PromptHelperService:
    """Service for building and managing prompts for LLM interactions"""
    
    @staticmethod
    def build_ticket_prompt(
        context: str,
        requirements: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        config: Optional[BreakdownConfig] = None
    ) -> str:
        """Build prompt for ticket description generation"""
        if config is None:
            config = BreakdownConfig()

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
                
        prompt_parts.append(f"""
Please format the response using EXACTLY this structure:

<ticket>
Title: [Clear, concise title]
Description: [Detailed description of the work required]

Technical Domain: [Primary technical area]
Required Skills: [Comma-separated list of key technical skills needed]
Story Points: [{config.min_story_points}-{config.max_story_points}]
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
- Story points should be between {config.min_story_points} and {config.max_story_points}
- Required skills should be specific technologies/frameworks
- Technical notes should include implementation guidance
""")
        
        return "".join(prompt_parts)

    @staticmethod
    def build_complexity_prompt(
        ticket_description: str,
        config: Optional[BreakdownConfig] = None
    ) -> str:
        """Build prompt for ticket complexity analysis"""
        if config is None:
            config = BreakdownConfig()

        return f"""
        Please analyze the following JIRA ticket description and provide:
        1. Estimated complexity (Low/Medium/High)
        2. Estimated story points ({config.min_story_points}-{config.max_story_points})
        3. Key technical considerations
        4. Potential risks
        
        Ticket Description:
        {ticket_description}
        """

    @staticmethod
    def build_epic_analysis_prompt(
        epic_summary: str,
        epic_description: str,
        config: Optional[BreakdownConfig] = None
    ) -> str:
        """Build prompt for analyzing an epic"""
        if config is None:
            config = BreakdownConfig()

        return f"""
        Please analyze the following JIRA epic and break it down into smaller tasks.

        Epic Title: {epic_summary}
        Epic Description: {epic_description}

        {config.to_prompt_constraints()}

        Please provide a structured breakdown in the following format:

        <analysis>
        Scope Analysis:
        - [Key aspects of the epic's scope]
        - [Technical considerations]
        - [Dependencies and integrations]

        Complexity Assessment:
        - Overall Complexity: [High/Medium/Low]
        - Technical Risk Areas: [List key risk areas]
        - Required Skills: [List required technical skills]

        Suggested Breakdown Structure:
        - [High-level breakdown strategy]
        - [Key components or areas]
        - [Integration points]
        </analysis>
        """

    @staticmethod
    def build_user_stories_prompt(
        epic_analysis: Dict[str, Any],
        config: Optional[BreakdownConfig] = None
    ) -> str:
        """Build prompt for generating user stories with Gherkin scenarios"""
        if config is None:
            config = BreakdownConfig()

        return f"""
        Please create user stories based on this epic analysis:

        {PromptHelperService._format_dict_for_prompt(epic_analysis)}

        First, provide a summary of planned stories:
        <summary>
        Total User Stories: [maximum {config.max_user_stories}]
        Key User Types: [list]
        Primary Value Streams: [list]
        </summary>

        Then, create {config.max_user_stories} or fewer user stories that represent valuable features or capabilities.
        For each user story, provide both a description and Gherkin scenarios:

        <user_story>
        Task: User Story - [What the user can do]
        Description: As a [user type], I want to [action] so that [benefit]
        Technical Domain: [Primary technical area]
        Complexity: [Low/Medium/High]
        Story Points: [{config.min_story_points}-{config.max_story_points}]
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
        epic_analysis: Dict[str, Any],
        config: Optional[BreakdownConfig] = None
    ) -> str:
        if config is None:
            config = BreakdownConfig()

        return f"""
Let's systematically break down this epic: "{epic_summary}"

Original Description:
{epic_description}

Technical Domains: {', '.join(epic_analysis.get('technical_domains', []))}

First, provide your breakdown strategy:
<strategy>
Total Planned Stories: [maximum {config.max_user_stories}]
Total Planned Technical Tasks: [maximum {config.max_technical_tasks}]
Breakdown Approach: [Brief explanation]
</strategy>

Please create the following breakdown:

1. Core User Stories (minimum 2, maximum {config.max_user_stories}):
<user_story>
Task: User Story - [Feature Name]
Description: As a [user], I want to [action] so that [benefit]
Technical Domain: [Area]
Complexity: [Low/Medium/High]
Story Points: [{config.min_story_points}-{config.max_story_points}]
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

    def build_task_breakdown_prompt(
        self,
        task_type: str,
        task_summary: str,
        epic_context: Dict[str, Any],
        config: Optional[BreakdownConfig] = None
    ) -> str:
        """Build prompt for breaking down a high-level task"""
        if config is None:
            config = BreakdownConfig()

        max_subtasks = (
            config.max_subtasks_per_story 
            if task_type == "USER-STORY" 
            else config.max_subtasks_per_tech_task
        )

        return f"""
        Please break down the following {task_type} into detailed subtasks.

        Task Summary: {task_summary}
        Epic Context: {epic_context['summary']}

        Constraints:
        - Create no more than {max_subtasks} subtasks
        - Story points per subtask should be between {config.min_story_points} and {config.max_story_points}
        - Focus on concrete, implementable units of work
        - Include clear acceptance criteria for each subtask

        Please provide the breakdown in the following format:

        <subtasks>
        [
            {{
                "title": "Subtask title",
                "description": "Detailed description",
                "acceptance_criteria": ["Criterion 1", "Criterion 2"],
                "story_points": story_points_value,
                "required_skills": ["Skill 1", "Skill 2"],
                "dependencies": ["Dependency 1"],
                "suggested_assignee": "Role or skill level"
            }},
            ...
        ]
        </subtasks>
        """ 