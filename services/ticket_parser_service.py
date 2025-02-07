from typing import Dict, Any, List, Optional
from loguru import logger
import xml.etree.ElementTree as ET
from io import StringIO
import re
import json

class TicketParserService:
    """Service for parsing LLM responses related to JIRA tickets"""

    @staticmethod
    def parse_ticket_description(response_text: str) -> Dict[str, Any]:
        """Parse the LLM response for ticket description into structured format"""
        logger.debug("Starting to parse ticket description")
        
        try:
            # Extract the ticket content between tags
            ticket_match = re.search(r'<ticket>(.*?)</ticket>', response_text, re.DOTALL)
            if not ticket_match:
                raise ValueError("No ticket content found between <ticket> tags")
                
            content = ticket_match.group(1)
            
            # Initialize the structured response
            ticket = {
                "title": "",
                "description": "",
                "technical_domain": "",
                "required_skills": [],
                "story_points": 0,
                "suggested_assignee": "",
                "complexity": "",
                "acceptance_criteria": [],
                "scenarios": [],
                "technical_notes": ""
            }
            
            # Extract basic fields
            title_match = re.search(r'Title:\s*(.+?)(?=\n|$)', content)
            if title_match:
                ticket["title"] = title_match.group(1).strip()
                
            desc_match = re.search(r'Description:\s*(.+?)(?=\nTechnical Domain:|$)', content, re.DOTALL)
            if desc_match:
                ticket["description"] = desc_match.group(1).strip()
                
            domain_match = re.search(r'Technical Domain:\s*(.+?)(?=\n|$)', content)
            if domain_match:
                ticket["technical_domain"] = domain_match.group(1).strip()
                
            skills_match = re.search(r'Required Skills:\s*(.+?)(?=\n|$)', content)
            if skills_match:
                ticket["required_skills"] = [s.strip() for s in skills_match.group(1).split(",")]
                
            points_match = re.search(r'Story Points:\s*(\d+)', content)
            if points_match:
                ticket["story_points"] = int(points_match.group(1))
                
            assignee_match = re.search(r'Suggested Assignee:\s*(.+?)(?=\n|$)', content)
            if assignee_match:
                ticket["suggested_assignee"] = assignee_match.group(1).strip()
                
            complexity_match = re.search(r'Complexity:\s*(.+?)(?=\n|$)', content)
            if complexity_match:
                ticket["complexity"] = complexity_match.group(1).strip()
            
            # Extract acceptance criteria
            ac_section = re.search(r'Acceptance Criteria:\s*\n(.*?)(?=\n\s*Scenarios:|$)', content, re.DOTALL)
            if ac_section:
                criteria = ac_section.group(1).strip().split('\n')
                ticket["acceptance_criteria"] = [c.strip('- ').strip() for c in criteria if c.strip()]
            
            # Extract Gherkin scenarios
            scenarios_section = re.search(r'Scenarios:(.*?)(?=\nTechnical Notes:|$)', content, re.DOTALL)
            if scenarios_section:
                scenario_blocks = re.finditer(r'Scenario:.*?(?=Scenario:|$)', scenarios_section.group(1), re.DOTALL)
                for block in scenario_blocks:
                    scenario = {
                        "name": "",
                        "steps": []
                    }
                    
                    # Get scenario name
                    name_match = re.search(r'Scenario:\s*(.+?)(?=\n|$)', block.group(0))
                    if name_match:
                        scenario["name"] = name_match.group(1).strip()
                    
                    # Get steps
                    steps = re.findall(r'(Given|When|Then|And)\s+(.+?)(?=\n|$)', block.group(0))
                    for step in steps:
                        scenario["steps"].append({
                            "keyword": step.group(1),
                            "text": step.group(2).strip()
                        })
                    
                    ticket["scenarios"].append(scenario)
            
            # Extract technical notes
            tech_notes_match = re.search(r'Technical Notes:\s*\n(.*?)(?=\n<\/ticket>|$)', content, re.DOTALL)
            if tech_notes_match:
                ticket["technical_notes"] = tech_notes_match.group(1).strip()
            
            logger.debug("Successfully parsed ticket description")
            return ticket
            
        except Exception as e:
            logger.error(f"Error parsing ticket description: {str(e)}")
            logger.error(f"Response text:\n{response_text}")
            raise

    @staticmethod
    def parse_epic_analysis(text: str) -> Dict[str, Any]:
        """Parse the epic analysis response into structured format"""
        sections = {
            "main_objective": "",
            "stakeholders": [],
            "core_requirements": [],
            "technical_domains": [],
            "dependencies": [],
            "challenges": []
        }
        
        current_section = None
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            lower_line = line.lower()
            
            if "main objective" in lower_line:
                current_section = "main_objective"
                continue
            elif "stakeholders" in lower_line:
                current_section = "stakeholders"
                continue
            elif "requirements" in lower_line:
                current_section = "core_requirements"
                continue
            elif "technical domains" in lower_line:
                current_section = "technical_domains"
                continue
            elif "dependencies" in lower_line:
                current_section = "dependencies"
                continue
            elif "challenges" in lower_line:
                current_section = "challenges"
                continue
                
            if current_section and line:
                if current_section == "main_objective":
                    sections[current_section] = line
                else:
                    if line.startswith(("- ", "* ", "• ")):
                        sections[current_section].append(line[2:].strip())
                    elif line[0].isdigit() and ". " in line:
                        sections[current_section].append(line.split(". ", 1)[1].strip())
                    elif line:
                        sections[current_section].append(line)
        
        return sections

    @staticmethod
    def parse_high_level_tasks(response: str) -> List[Dict[str, Any]]:
        """Parse high level tasks from LLM response"""
        tasks = []
        try:
            logger.debug("Starting to parse high level tasks")
            logger.debug(f"Raw response:\n{response}")
            
            # First extract the summary if present
            summary_match = re.search(r'<summary>(.*?)</summary>', response, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1)
                logger.info(f"Task Summary:\n{summary.strip()}")
            
            # Extract user stories
            user_stories = re.findall(r'<user_story>(.*?)</user_story>', response, re.DOTALL)
            technical_tasks = re.findall(r'<technical_task>(.*?)</technical_task>', response, re.DOTALL)
            
            logger.debug(f"Found {len(user_stories)} user stories and {len(technical_tasks)} technical tasks")
            
            # Parse user stories
            for story in user_stories:
                task = TicketParserService._parse_task_content(story, "User Story")
                if task:
                    tasks.append(task)
            
            # Parse technical tasks
            for tech_task in technical_tasks:
                task = TicketParserService._parse_task_content(tech_task, "Technical Task")
                if task:
                    tasks.append(task)
            
            logger.debug(f"Successfully parsed {len(tasks)} total tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to parse high level tasks: {str(e)}")
            logger.error(f"Response that caused error:\n{response}")
            return [{
                "name": "Error in task breakdown",
                "description": f"Failed to parse tasks: {str(e)}",
                "technical_domain": "Unknown",
                "complexity": "Medium",
                "dependencies": []
            }]

    @staticmethod
    def _parse_task_content(content: str, task_type: str) -> Optional[Dict[str, Any]]:
        """Helper method to parse individual task content"""
        try:
            lines = content.strip().split('\n')
            task = {
                "type": task_type,
                "name": "",
                "description": "",
                "technical_domain": "",
                "complexity": "",
                "dependencies": []
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith("Task:"):
                    task["name"] = line.split(":", 1)[1].strip()
                elif line.startswith("Description:"):
                    task["description"] = line.split(":", 1)[1].strip()
                elif line.startswith("Technical Domain:"):
                    task["technical_domain"] = line.split(":", 1)[1].strip()
                elif line.startswith("Complexity:"):
                    task["complexity"] = line.split(":", 1)[1].strip()
                elif line.startswith("Dependencies:"):
                    deps = line.split(":", 1)[1].strip()
                    task["dependencies"] = [
                        d.strip() 
                        for d in deps.split(",")
                        if d.strip() and d.strip().lower() != "none"
                    ]
            
            return task if task["name"] else None
            
        except Exception as e:
            logger.error(f"Failed to parse task content: {str(e)}")
            logger.error(f"Content:\n{content}")
            return None

    @staticmethod
    def _extract_code_blocks(content: str) -> List[Dict[str, str]]:
        """Extract code blocks with their language from content"""
        code_blocks = []
        
        # Match JIRA-style code blocks: {code:language}...{code}
        jira_matches = re.finditer(r'\{code:(\w+)\}(.*?)\{code\}', content, re.DOTALL)
        for match in jira_matches:
            code_blocks.append({
                "language": match.group(1),
                "code": match.group(2).strip()
            })
        
        # Match markdown-style code blocks: ```language...```
        markdown_matches = re.finditer(r'```(\w*)\n(.*?)```', content, re.DOTALL)
        for match in markdown_matches:
            language = match.group(1) or 'text'  # Default to 'text' if no language specified
            code_blocks.append({
                "language": language,
                "code": match.group(2).strip()
            })
            
        return code_blocks

    @staticmethod
    def _extract_implementation_details(content: str) -> Dict[str, Any]:
        """Extract implementation details section from content"""
        details = {
            "technical_approach": "",
            "code_blocks": [],
            "key_considerations": []
        }
        
        # Find Implementation Details section - handle both numbered and unnumbered formats
        impl_patterns = [
            r'Implementation Details:?(.*?)(?=\n\*\*\w+:|$)',  # Technical tasks format
            r'Implementation Overview:(.*?)(?=\nTechnical Domain|$)',  # User stories format
            r'Implementation Details:(.*?)(?=\nAcceptance Criteria|$)'  # Subtasks format
        ]
        
        impl_content = None
        for pattern in impl_patterns:
            impl_match = re.search(pattern, content, re.DOTALL)
            if impl_match:
                impl_content = impl_match.group(1).strip()
                break
                
        if impl_content:
            # Extract Technical Approach - handle both numbered and unnumbered formats
            approach_patterns = [
                r'(?:Technical Approach:|1\.)(.*?)(?=\n\d\.|$)',
                r'Technical Approach:(.*?)(?=\n\d\.|Example Implementation|$)',
                r'(?:Implementation Strategy:|1\.)(.*?)(?=\n\d\.|Code Considerations|$)'
            ]
            
            for pattern in approach_patterns:
                tech_approach = re.search(pattern, impl_content, re.DOTALL)
                if tech_approach:
                    details["technical_approach"] = tech_approach.group(1).strip()
                    break
            
            # Extract code blocks
            details["code_blocks"] = TicketParserService._extract_code_blocks(impl_content)
            
            # Extract key considerations - handle various formats
            considerations_patterns = [
                r'(?:Key implementation steps:|Key Implementation Considerations:|3\.)(.*?)(?=\n\*\*\w+:|$)',
                r'Key Implementation Considerations:(.*?)(?=\n\w+:|$)',
                r'(?:Testing Approach:|3\.)(.*?)(?=\n\w+:|$)'
            ]
            
            for pattern in considerations_patterns:
                considerations_match = re.search(pattern, impl_content, re.DOTALL)
                if considerations_match:
                    considerations = considerations_match.group(1).strip()
                    details["key_considerations"] = [
                        c.strip('- ').strip()
                        for c in considerations.split('\n')
                        if c.strip('- ').strip()
                    ]
                    break
        
        return details

    @staticmethod
    def parse_user_stories(response: str) -> List[Dict[str, Any]]:
        """Parse user stories including implementation details from LLM response"""
        stories = []
        try:
            story_matches = re.findall(r'<user_story>(.*?)</user_story>', response, re.DOTALL)
            
            for story in story_matches:
                # Extract basic story information
                task_name = re.search(r'Task:\s*(.+?)(?=\n|$)', story)
                description = re.search(r'Description:\s*(.+?)(?=\n|Implementation Overview|Technical)', story)
                domain = re.search(r'Technical Domain:\s*(.+?)(?=\n|$)', story)
                complexity = re.search(r'Complexity:\s*(.+?)(?=\n|$)', story)
                value = re.search(r'Business Value:\s*(.+?)(?=\n|$)', story)
                dependencies = re.search(r'Dependencies:\s*(.+?)(?=\n|Modern)', story)
                modern_approaches = re.search(r'Modern Approaches:\s*(.+?)(?=\n|$)', story)
                accessibility = re.search(r'Accessibility Requirements:\s*(.+?)(?=\n|$)', story)
                integration = re.search(r'Integration Points:\s*(.+?)(?=\n|$)', story)
                
                # Extract User Experience section
                ux_section = re.search(r'User Experience:(.*?)(?=\nScenarios:|$)', story, re.DOTALL)
                ux_details = {}
                if ux_section:
                    pain_points = re.search(r'Current Pain Points:\s*(.+?)(?=\n|$)', ux_section.group(1))
                    success_metrics = re.search(r'Success Metrics:\s*(.+?)(?=\n|$)', ux_section.group(1))
                    similar_impl = re.search(r'Similar Implementations:\s*(.+?)(?=\n|$)', ux_section.group(1))
                    ux_details = {
                        "pain_points": pain_points.group(1).strip() if pain_points else "",
                        "success_metrics": success_metrics.group(1).strip() if success_metrics else "",
                        "similar_implementations": similar_impl.group(1).strip() if similar_impl else ""
                    }
                
                # Extract implementation details
                implementation_details = TicketParserService._extract_implementation_details(story)
                
                # Extract scenarios
                scenarios_text = re.search(r'Scenarios:(.*?)(?=</user_story>|$)', story, re.DOTALL)
                scenarios = []
                
                if scenarios_text:
                    scenario_matches = re.findall(r'Scenario:.*?(?=Scenario:|$)', scenarios_text.group(1), re.DOTALL)
                    for scenario in scenario_matches:
                        scenario_dict = {
                            "name": re.search(r'Scenario:\s*(.+?)(?=\n|$)', scenario).group(1).strip(),
                            "steps": []
                        }
                        
                        steps = re.findall(r'(Given|When|Then|And)\s+(.+?)(?=\n|$)', scenario)
                        for keyword, step_text in steps:
                            scenario_dict["steps"].append({
                                "keyword": keyword,
                                "text": step_text.strip()
                            })
                        
                        scenarios.append(scenario_dict)
                
                if task_name and description:
                    stories.append({
                        "type": "User Story",
                        "name": task_name.group(1).strip(),
                        "description": description.group(1).strip(),
                        "technical_domain": domain.group(1).strip() if domain else "",
                        "complexity": complexity.group(1).strip() if complexity else "Medium",
                        "business_value": value.group(1).strip() if value else "Medium",
                        "dependencies": [d.strip() for d in dependencies.group(1).split(',')] if dependencies else [],
                        "modern_approaches": modern_approaches.group(1).strip() if modern_approaches else "",
                        "accessibility_requirements": accessibility.group(1).strip() if accessibility else "",
                        "integration_points": integration.group(1).strip() if integration else "",
                        "implementation_details": implementation_details,
                        "user_experience": ux_details,
                        "scenarios": scenarios
                    })
                
            return stories
            
        except Exception as e:
            logger.error(f"Failed to parse user stories: {str(e)}")
            logger.error(f"Response that caused error:\n{response}")
            return []

    @staticmethod
    def parse_technical_tasks(response: str) -> List[Dict[str, Any]]:
        """Parse technical tasks from LLM response"""
        tasks = []
        try:
            logger.debug("Starting to parse technical tasks")
            logger.debug(f"Raw response:\n{response}")
            
            # Extract technical tasks
            task_matches = re.findall(r'<technical_task>\n?(.*?)</technical_task>', response, re.DOTALL)
            logger.debug(f"Found {len(task_matches)} technical tasks")
            
            for task in task_matches:
                try:
                    # Extract fields using more flexible patterns
                    fields = {
                        "task_name": re.search(r'\*\*Task:\*\*\s*(?:Technical Task - )?(.*?)(?=\n\*\*|\n\s*Implementation Details|\n\s*$)', task, re.DOTALL),
                        "description": re.search(r'\*\*Description:\*\*\s*(.*?)(?=\n\*\*|\n\s*Implementation Details|\n\s*$)', task, re.DOTALL),
                        "technical_domain": re.search(r'\*\*Technical Domain:\*\*\s*(.*?)(?=\n\*\*|\n\s*$)', task),
                        "complexity": re.search(r'\*\*Complexity:\*\*\s*(.*?)(?=\n\*\*|\n\s*$)', task),
                        "dependencies": re.search(r'\*\*Dependencies:\*\*\s*(.*?)(?=\n\*\*|\n\s*$)', task),
                        "implementation_notes": re.search(r'\*\*Implementation Notes:\*\*\s*(.*?)(?=\n\*\*|\n\s*$)', task),
                        "modern_practices": re.search(r'\*\*Modern Practices:\*\*\s*(.*?)(?=\n\*\*|\n\s*$)', task),
                        "security_considerations": re.search(r'\*\*Security Considerations:\*\*\s*(.*?)(?=\n\*\*|\n\s*$)', task)
                    }
                    
                    # Log raw field matches for debugging
                    logger.debug("Raw field matches:")
                    for field, match in fields.items():
                        logger.debug(f"{field}: {match.group(1) if match else 'None'}")
                    
                    # Extract implementation details
                    implementation_details = TicketParserService._extract_implementation_details(task)
                    
                    # Check required fields
                    required_fields = ["task_name", "description", "technical_domain", "complexity"]
                    missing = [field for field in required_fields if not fields[field]]
                    
                    if not missing:
                        parsed_task = {
                            "type": "Technical Task",
                            "name": f"Technical Task - {fields['task_name'].group(1).strip()}",
                            "description": fields['description'].group(1).strip(),
                            "technical_domain": fields['technical_domain'].group(1).strip(),
                            "complexity": fields['complexity'].group(1).strip(),
                            "dependencies": [d.strip() for d in fields['dependencies'].group(1).split(',')] if fields['dependencies'] else [],
                            "implementation_notes": fields['implementation_notes'].group(1).strip() if fields['implementation_notes'] else "",
                            "modern_practices": fields['modern_practices'].group(1).strip() if fields['modern_practices'] else "",
                            "security_considerations": fields['security_considerations'].group(1).strip() if fields['security_considerations'] else "",
                            "implementation_details": implementation_details
                        }
                        tasks.append(parsed_task)
                        logger.debug(f"Successfully parsed task: {parsed_task['name']}")
                        logger.debug(f"Task details: {json.dumps(parsed_task, indent=2)}")
                    else:
                        logger.warning(f"Skipping task due to missing required fields: {', '.join(missing)}")
                        logger.warning(f"Task content:\n{task}")
                
                except Exception as e:
                    logger.error(f"Failed to parse individual task: {str(e)}")
                    logger.error(f"Task content that caused error:\n{task}")
                    continue
            
            logger.debug(f"Successfully parsed {len(tasks)} technical tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to parse technical tasks: {str(e)}")
            logger.error(f"Response that caused error:\n{response}")
            return []

    @staticmethod
    def parse_subtasks(text: str) -> List[Dict[str, Any]]:
        """Parse the subtasks response into structured format"""
        subtasks = []
        try:
            logger.debug("Starting to parse subtasks")
            logger.debug(f"Raw response:\n{text}")
            
            # Extract subtasks using XML tags
            subtask_matches = re.findall(r'<subtask>(.*?)</subtask>', text, re.DOTALL)
            logger.debug(f"Found {len(subtask_matches)} subtask blocks")
            
            for subtask_content in subtask_matches:
                try:
                    subtask = {
                        "title": "",
                        "description": "",
                        "acceptance_criteria": [],
                        "story_points": 1,  # Default value
                        "required_skills": [],
                        "dependencies": [],
                        "suggested_assignee": "Unassigned",  # Default value
                        "implementation_details": {}
                    }
                    
                    # Parse each field
                    title_match = re.search(r'Title:\s*(.+?)(?=\n|$)', subtask_content)
                    if title_match:
                        subtask["title"] = title_match.group(1).strip()
                    
                    desc_match = re.search(r'Description:\s*(.+?)(?=\n\s*Implementation Details|$)', subtask_content, re.DOTALL)
                    if desc_match:
                        subtask["description"] = desc_match.group(1).strip()
                    
                    # Extract implementation details
                    subtask["implementation_details"] = TicketParserService._extract_implementation_details(subtask_content)
                    
                    # Parse acceptance criteria
                    ac_section = re.search(r'Acceptance Criteria:(.*?)(?=\n\s*Story Points|$)', subtask_content, re.DOTALL)
                    if ac_section:
                        criteria = [
                            c.strip('- ').strip()
                            for c in ac_section.group(1).strip().split('\n')
                            if c.strip('- ').strip()
                        ]
                        subtask["acceptance_criteria"] = criteria
                    
                    points_match = re.search(r'Story Points:\s*(\d+)', subtask_content)
                    if points_match:
                        subtask["story_points"] = int(points_match.group(1))
                    
                    skills_match = re.search(r'Required Skills:\s*(.+?)(?=\n|$)', subtask_content)
                    if skills_match:
                        skills = skills_match.group(1).strip()
                        subtask["required_skills"] = [s.strip() for s in skills.split(",") if s.strip()]
                    
                    deps_match = re.search(r'Dependencies:\s*(.+?)(?=\n|$)', subtask_content)
                    if deps_match:
                        deps = deps_match.group(1).strip()
                        subtask["dependencies"] = [d.strip() for d in deps.split(",") if d.strip()]
                    
                    assignee_match = re.search(r'Suggested Assignee:\s*(.+?)(?=\n|$)', subtask_content)
                    if assignee_match:
                        subtask["suggested_assignee"] = assignee_match.group(1).strip()
                    
                    # Validate required fields before adding
                    if subtask["title"] and subtask["description"] and subtask["acceptance_criteria"]:
                        subtasks.append(subtask)
                    else:
                        logger.warning(f"Skipping subtask due to missing required fields: {json.dumps(subtask, indent=2)}")
                    
                except Exception as e:
                    logger.error(f"Failed to parse subtask content: {str(e)}")
                    logger.error(f"Subtask content:\n{subtask_content}")
                    continue
            
            logger.debug(f"Successfully parsed {len(subtasks)} valid subtasks")
            return subtasks
            
        except Exception as e:
            logger.error(f"Failed to parse subtasks: {str(e)}")
            logger.error(f"Full text that caused error:\n{text}")
            return [] 