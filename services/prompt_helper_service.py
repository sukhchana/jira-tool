from typing import Dict, Any, Optional, List
import os

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
        Total Technical Domains: [number]
        Total Core Requirements: [number]
        Total Dependencies: [number]
        Total Challenges: [number]
        Research Findings: [key insights from internet search]
        </summary>

        Then provide the detailed analysis:
        <analysis>
        Main Objective: [Clear statement of the epic's primary goal]

        Stakeholders:
        [List key stakeholders]

        Core Requirements:
        [List main requirements]

        Technical Domains:
        [List technical areas involved, including current best practices from research]

        Dependencies:
        [List external dependencies]

        Challenges:
        [List potential challenges, incorporating insights from similar implementations]

        Industry Context:
        [Relevant industry standards, trends, and best practices found through research]
        </analysis>
        """

    @staticmethod
    def build_user_stories_prompt(epic_analysis: Dict[str, Any]) -> str:
        """Build prompt for generating user stories with Gherkin scenarios"""
        return f"""
        Please create user stories based on this epic analysis. 
        Use internet search to:
        1. Research similar features/capabilities in existing products or services
        2. Identify modern UX patterns and best practices for these types of features
        3. Find common user pain points and their solutions
        4. Research accessibility considerations and standards
        5. Discover industry benchmarks and user expectations
        6. Identify potential integration points with popular tools/platforms

        Epic Analysis:
        {PromptHelperService._format_dict_for_prompt(epic_analysis)}

        First, provide a summary of your research and planned stories:
        <research_summary>
        Similar Implementations Found: [list key examples]
        Modern UX Patterns Identified: [list relevant patterns]
        Key User Pain Points: [list common issues]
        Accessibility Considerations: [list key requirements]
        Integration Opportunities: [list potential integrations]
        </research_summary>

        <story_planning>
        Total User Stories: [number]
        Key User Types: [list]
        Primary Value Streams: [list]
        Implementation Recommendations: [based on research]
        </story_planning>

        Then, create 3-5 user stories that represent valuable features or capabilities.
        For each user story, provide both a description and Gherkin scenarios:

        <user_story>
        Task: User Story - [What the user can do]
        Description: As a [user type], I want to [action] so that [benefit]

        Implementation Overview:
        1. Technical Approach:
        {{code:text}}
        - Frontend: [Describe frontend implementation approach]
        - Backend: [Describe backend implementation approach]
        - Data Model: [Describe data structure/schema]
        - APIs: [List required APIs/endpoints]
        {{code}}

        2. Example Implementation:
        {{code:javascript}}
        // Frontend Component Example
        const UserFeature = () => {{
          const [data, setData] = useState(null);
          
          const handleAction = async () => {{
            // Implementation details
          }};
          
          return (
            <div>
              {{/* UI components */}}
            </div>
          );
        }};
        {{code}}

        {{code:python}}
        # Backend API Example
        @router.post("/api/feature")
        async def handle_feature(request: FeatureRequest):
            # Implementation logic
            return FeatureResponse(...)
        {{code}}

        3. Key Implementation Considerations:
        - Performance requirements
        - Error handling approach
        - Data validation rules
        - Security measures

        Technical Domain: [Primary technical area]
        Complexity: [Low/Medium/High]
        Business Value: [High/Medium/Low]
        Dependencies: [List any dependencies]
        Modern Approaches: [Relevant patterns/solutions from research]
        Accessibility Requirements: [Key considerations]
        Integration Points: [Potential system/tool integrations]

        User Experience:
        - Current Pain Points: [Issues this story addresses]
        - Success Metrics: [How to measure success]
        - Similar Implementations: [Examples from research]

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

        Scenario: [Accessibility scenario]
        Given [user with specific needs]
        When [action is taken]
        Then [expected accessible outcome]
        </user_story>

        Remember:
        - Each story should have at least 3 scenarios (happy path, error path, and accessibility)
        - Include implementation examples and code snippets
        - Use JIRA's {{code:language}} format for code blocks
        - Provide both frontend and backend considerations
        - Include data model and API specifications
        - Use clear, specific Gherkin steps
        - Scenarios should be testable
        - Include relevant business context
        - Consider edge cases and error conditions
        - Use consistent terminology
        - Incorporate insights from research
        - Consider integration possibilities
        - Address identified pain points
        - Follow modern UX patterns
        - Ensure accessibility compliance
        """

    @staticmethod
    def build_technical_tasks_prompt(user_stories: List[Dict[str, Any]], epic_analysis: Dict[str, Any]) -> str:
        """Build prompt for technical tasks generation"""
        return f"""
        Please create technical tasks needed to implement these user stories.
        Use internet search to:
        1. Research current technical approaches and best practices
        2. Identify modern tools and frameworks that could be beneficial
        3. Find examples of similar implementations
        4. Stay updated on latest security considerations and compliance requirements

        User Stories:
        {PromptHelperService._format_user_stories(user_stories)}

        Technical Context:
        {PromptHelperService._format_epic_analysis(epic_analysis)}

        First, provide an implementation strategy:
        <strategy>
        Total Technical Tasks: [number]
        Key Technical Components: [list]
        Implementation Approach: [brief explanation]
        Research Findings: [key technical insights from search]
        Recommended Tools/Frameworks: [based on current best practices]
        </strategy>

        Then, for each user story, create the necessary technical tasks. 
        CRITICAL: Each technical task MUST be wrapped in XML tags exactly like this example:

        <technical_task>
        **Task:** Technical Task - Set up OAuth2 Authentication
        **Description:** Implement OAuth2 authentication flow using the latest security standards.

        Implementation Details:
        1. Set up OAuth2 client configuration:
        {{code:python}}
        oauth_config = {{
            "client_id": os.getenv("OAUTH_CLIENT_ID"),
            "client_secret": os.getenv("OAUTH_CLIENT_SECRET"),
            "redirect_uri": "https://your-app/callback",
            "scope": ["openid", "profile", "email"]
        }}
        {{code}}

        2. Implement authorization code flow with PKCE:
        {{code:python}}
        from authlib.integrations.requests_client import OAuth2Session
        import hashlib
        import base64
        import secrets

        def generate_pkce_pair():
            code_verifier = secrets.token_urlsafe(64)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            return code_verifier, code_challenge
        {{code}}

        3. Key implementation steps:
        - Store tokens securely in encrypted session
        - Implement token refresh mechanism
        - Add error handling for auth failures
        - Set up proper CORS for OAuth redirects

        **Technical Domain:** Authentication & Security
        **Complexity:** Medium
        **Dependencies:** User Story - Secure Login
        **Implementation Notes:** Use industry-standard OAuth2 libraries
        **Modern Practices:** Implement PKCE, use secure token storage
        **Security Considerations:** Follow OWASP guidelines for OAuth2
        </technical_task>

        FORMATTING RULES - YOU MUST FOLLOW THESE EXACTLY:
        1. Start each task with <technical_task> on its own line
        2. End each task with </technical_task> on its own line
        3. Each field inside must:
           - Start with double asterisks and end with colon (e.g., **Task:**)
           - Be on its own line
           - Have a space after the colon
        4. Description field should include:
           - Clear overview of what needs to be done
           - Implementation details with numbered steps
           - Code snippets where applicable, wrapped in {{code:language}} tags
           - Configuration examples if needed
           - Key implementation steps and considerations
        5. Fields must appear in this exact order:
           - Task
           - Description (with implementation details)
           - Technical Domain
           - Complexity
           - Dependencies
           - Implementation Notes
           - Modern Practices
           - Security Considerations
        6. NO blank lines between fields within a task (except in Description for readability)
        7. ONE blank line between different tasks
        8. NO other text or formatting outside the XML tags
        9. Code snippets must use JIRA's {{code:language}} format

        Requirements:
        - Each user story should have 1-2 technical tasks
        - Tasks should be specific and implementable
        - No task should take more than 3 days
        - Include both frontend and backend work where relevant
        - Consider infrastructure and testing needs
        - Break down complex tasks into smaller, manageable pieces
        - Incorporate modern best practices found through research
        - Consider security implications for each task
        - Include relevant code snippets and examples
        - Use proper JIRA formatting for code blocks

        IMPORTANT: Your response must be parseable XML. Each technical task must be a complete XML element with proper opening and closing tags.
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
        Technical Components: [list of technical components involved]
        </summary>

        Then, for each subtask, provide ALL of the following details in this format:

        <subtask>
        Title: [Clear, specific title]
        Description: [Detailed technical description]

        Implementation Details:
        1. Technical Approach:
        {{code:text}}
        - Implementation Strategy: [Describe the approach]
        - Components Affected: [List components]
        - Dependencies: [List dependencies]
        - Configuration Changes: [If needed]
        {{code}}

        2. Code Considerations:
        {{code:language}}
        // Example code or pseudo-code showing key implementation aspects
        // Include relevant code patterns or structures
        // Show configuration examples if applicable
        {{code}}

        3. Testing Approach:
        {{code:text}}
        - Unit Tests: [Describe test cases]
        - Integration Tests: [Describe test scenarios]
        - Performance Tests: [If applicable]
        {{code}}

        Acceptance Criteria:
        - [List specific, testable criteria]
        - [Include performance requirements]
        - [Include error handling requirements]

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
        - Include implementation examples and code snippets
        - Use JIRA's {{code:language}} format for code blocks
        - Consider testing needs
        - Story points should be between 1-5
        - Titles should be clear and specific
        - Provide concrete implementation guidance
        - Include configuration examples where relevant
        - Specify testing requirements
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