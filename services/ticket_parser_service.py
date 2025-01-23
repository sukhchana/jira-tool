from typing import Dict, Any, List, Optional
from loguru import logger
import xml.etree.ElementTree as ET
from io import StringIO
import re
import json

class TicketParserService:
    """Service for parsing LLM responses related to JIRA tickets"""

    @staticmethod
    def parse_ticket_description(response_text: str) -> Dict[str, str]:
        """Parse the LLM response for ticket description into structured format"""
        logger.debug("Starting to parse ticket description")
        sections = {
            "summary": "",
            "description": "",
            "acceptance_criteria": "",
            "technical_notes": ""
        }
        
        try:
            current_section = None
            lines = response_text.split("\n")
            
            for line in lines:
                line = line.strip()
                lower_line = line.lower()
                
                if "summary:" in lower_line:
                    current_section = "summary"
                    continue
                elif "description:" in lower_line:
                    current_section = "description"
                    continue
                elif "acceptance criteria:" in lower_line:
                    current_section = "acceptance_criteria"
                    continue
                elif "technical notes:" in lower_line:
                    current_section = "technical_notes"
                    continue
                
                if current_section and line:
                    sections[current_section] += line + "\n"
                
            result = {k: v.strip() for k, v in sections.items()}
            logger.debug("Successfully parsed ticket description")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing ticket description: {str(e)}")
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
                        "acceptance_criteria": "",
                        "story_points": 1,  # Default value
                        "required_skills": [],
                        "dependencies": [],
                        "suggested_assignee": "Unassigned"  # Default value
                    }
                    
                    # Parse each field
                    title_match = re.search(r'Title:\s*(.+?)(?=\n|$)', subtask_content)
                    if title_match:
                        subtask["title"] = title_match.group(1).strip()
                    
                    desc_match = re.search(r'Description:\s*(.+?)(?=\n|$)', subtask_content, re.DOTALL)
                    if desc_match:
                        subtask["description"] = desc_match.group(1).strip()
                    
                    ac_match = re.search(r'Acceptance Criteria:\s*(.+?)(?=\n|$)', subtask_content, re.DOTALL)
                    if ac_match:
                        subtask["acceptance_criteria"] = ac_match.group(1).strip()
                    
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

    @staticmethod
    def parse_user_stories(response: str) -> List[Dict[str, Any]]:
        """Parse user stories from LLM response"""
        stories = []
        try:
            logger.debug("Starting to parse user stories")
            logger.debug(f"Raw response:\n{response}")
            
            # Extract summary if present
            summary_match = re.search(r'<summary>(.*?)</summary>', response, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1)
                logger.info(f"User Stories Summary:\n{summary.strip()}")
            
            # Extract user stories
            story_matches = re.findall(r'<user_story>(.*?)</user_story>', response, re.DOTALL)
            logger.debug(f"Found {len(story_matches)} user stories")
            
            for story in story_matches:
                parsed_story = TicketParserService._parse_task_content(story, "User Story")
                if parsed_story:
                    # Add business value field specific to user stories
                    if "Business Value:" in story:
                        value_match = re.search(r'Business Value:\s*(\w+)', story)
                        if value_match:
                            parsed_story["business_value"] = value_match.group(1)
                    stories.append(parsed_story)
            
            logger.debug(f"Successfully parsed {len(stories)} user stories")
            return stories
            
        except Exception as e:
            logger.error(f"Failed to parse user stories: {str(e)}")
            logger.error(f"Response that caused error:\n{response}")
            return [{
                "type": "User Story",
                "name": "Error in user story parsing",
                "description": f"Failed to parse user stories: {str(e)}",
                "technical_domain": "Unknown",
                "complexity": "Medium",
                "dependencies": [],
                "business_value": "Medium"
            }]

    @staticmethod
    def parse_technical_tasks(response: str) -> List[Dict[str, Any]]:
        """Parse technical tasks from LLM response"""
        tasks = []
        try:
            logger.debug("Starting to parse technical tasks")
            logger.debug(f"Raw response:\n{response}")
            
            # Extract strategy if present
            strategy_match = re.search(r'<strategy>(.*?)</strategy>', response, re.DOTALL)
            if strategy_match:
                strategy = strategy_match.group(1)
                logger.info(f"Implementation Strategy:\n{strategy.strip()}")
            
            # Extract technical tasks
            task_matches = re.findall(r'<technical_task>(.*?)</technical_task>', response, re.DOTALL)
            logger.debug(f"Found {len(task_matches)} technical tasks")
            
            for task in task_matches:
                parsed_task = TicketParserService._parse_task_content(task, "Technical Task")
                if parsed_task:
                    # Add implementation notes field specific to technical tasks
                    if "Implementation Notes:" in task:
                        notes_match = re.search(r'Implementation Notes:\s*(.+?)(?=\n|$)', task, re.DOTALL)
                        if notes_match:
                            parsed_task["implementation_notes"] = notes_match.group(1).strip()
                    tasks.append(parsed_task)
            
            logger.debug(f"Successfully parsed {len(tasks)} technical tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to parse technical tasks: {str(e)}")
            logger.error(f"Response that caused error:\n{response}")
            return [{
                "type": "Technical Task",
                "name": "Error in technical task parsing",
                "description": f"Failed to parse technical tasks: {str(e)}",
                "technical_domain": "Unknown",
                "complexity": "Medium",
                "dependencies": [],
                "implementation_notes": "Error during parsing"
            }] 