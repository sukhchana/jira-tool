import os
from datetime import datetime, UTC
from typing import Dict, Any, List

import yaml
from loguru import logger

from models.code_example import CodeExample
from models.implementation_approach import ImplementationApproach
from models.research_summary import ResearchSummary
from models.test_plan import TestPlan


class ProposedTicketsService:
    """Service for tracking proposed JIRA tickets in YAML format"""

    def __init__(self, epic_key: str, execution_id: str):
        """Initialize with epic key and execution ID"""
        self.epic_key = epic_key
        self.execution_id = execution_id
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.filename = f"proposed_tickets/PROPOSED_{epic_key}_{timestamp}.yaml"

        # Initialize ID counters
        self.id_counters = {
            "USER-STORY": 0,
            "TECHNICAL-TASK": 0,
            "SUB-TASK": 0,
            "SCENARIO": 0
        }

        # Ensure directory exists
        os.makedirs("proposed_tickets", exist_ok=True)

        # Initialize the YAML structure with separate lists
        self.tickets_data = {
            "execution_id": execution_id,
            "epic_key": epic_key,
            "timestamp": datetime.now(UTC).isoformat(),
            "user_stories": [],  # Separate list for user stories
            "technical_tasks": [],  # Separate list for technical tasks
            "subtasks": {}
        }

    def _generate_id(self, type_prefix: str) -> str:
        """Generate a sequential ID for a given type"""
        self.id_counters[type_prefix] += 1
        return f"{type_prefix}-{self.id_counters[type_prefix]}"

    def add_high_level_task(self, task: Dict[str, Any]) -> str:
        """Add a high-level task (user story or technical task)"""
        # Determine task type and generate ID
        is_user_story = task.get("type") == "User Story"
        type_prefix = "USER-STORY" if is_user_story else "TECHNICAL-TASK"
        task_id = self._generate_id(type_prefix)

        task_data = {
            "id": task_id,
            "type": task.get("type", "Technical Task"),
            "title": task.get("title", task.get("name", "")),  # Handle both title and name for backward compatibility
            "description": task.get("description", ""),
            "technical_domain": task.get("technical_domain", ""),
            "complexity": task.get("complexity", "Medium"),
            "dependencies": task.get("dependencies", []),
            "business_value": task.get("business_value"),
            "implementation_notes": task.get("implementation_notes"),
            "parent_id": self.epic_key,
            "implementation_details": task.get("implementation_details", {}),
            "code_blocks": [
                {
                    "language": block.get("language", "text"),
                    "description": block.get("description", ""),
                    "code": block.get("code", ""),
                    "test_cases": [
                        {
                            "description": test_case.get("description", ""),
                            "code": test_case.get("code", "")
                        }
                        for test_case in block.get("test_cases", [])
                    ]
                }
                for block in task.get("code_blocks", [])
            ],
            "research_summary": {
                "pain_points": task.get("research_summary", {}).get("pain_points", ""),
                "success_metrics": task.get("research_summary", {}).get("success_metrics", ""),
                "similar_implementations": task.get("research_summary", {}).get("similar_implementations", ""),
                "modern_approaches": task.get("research_summary", {}).get("modern_approaches", ""),
                "performance_considerations": task.get("research_summary", {}).get("performance_considerations", ""),
                "security_implications": task.get("research_summary", {}).get("security_implications", ""),
                "maintenance_aspects": task.get("research_summary", {}).get("maintenance_aspects", "")
            } if task.get("research_summary") else None
        }

        # Add user story specific fields
        if is_user_story:
            task_data.update({
                "modern_approaches": task.get("modern_approaches"),
                "accessibility_requirements": task.get("accessibility_requirements"),
                "integration_points": task.get("integration_points"),
                "user_experience": task.get("user_experience", {}),
                "scenarios": [
                    {
                        "id": self._generate_id("SCENARIO"),
                        "name": scenario.get("name", ""),
                        "steps": scenario.get("steps", []),
                        "expected_result": scenario.get("expected_result", ""),
                        "preconditions": scenario.get("preconditions", []),
                        "postconditions": scenario.get("postconditions", [])
                    }
                    for scenario in task.get("scenarios", [])
                ]
            })
        else:
            # Add technical task specific fields
            task_data.update({
                "modern_practices": task.get("modern_practices"),
                "security_considerations": task.get("security_considerations")
            })

        # Add to appropriate list
        if is_user_story:
            self.tickets_data["user_stories"].append(task_data)
        else:
            self.tickets_data["technical_tasks"].append(task_data)

        return task_id

    def add_subtasks(self, parent_name: str, subtasks: List[Dict[str, Any]], parent_id: str) -> List[str]:
        """Add subtasks for a parent task with parent ID reference"""
        subtask_ids = []
        self.tickets_data["subtasks"][parent_name] = []

        for subtask in subtasks:
            subtask_id = self._generate_id("SUB-TASK")
            subtask_ids.append(subtask_id)

            self.tickets_data["subtasks"][parent_name].append({
                "id": subtask_id,
                "parent_id": parent_id,  # Add reference to parent ID
                "title": subtask["title"],
                "description": subtask["description"],
                "acceptance_criteria": subtask["acceptance_criteria"],
                "story_points": subtask["story_points"],
                "required_skills": subtask["required_skills"],
                "dependencies": subtask["dependencies"],
                "suggested_assignee": subtask["suggested_assignee"],
                "implementation_details": subtask.get("implementation_details", {}),
                "code_blocks": [
                    {
                        "language": block.get("language", "text"),
                        "description": block.get("description", ""),
                        "code": block.get("code", ""),
                        "test_cases": [
                            {
                                "description": test_case.get("description", ""),
                                "code": test_case.get("code", "")
                            }
                            for test_case in block.get("test_cases", [])
                        ]
                    }
                    for block in subtask.get("code_blocks", [])
                ],
                "test_plan": {
                    "unit_tests": subtask.get("test_plan", {}).get("unit_tests", []),
                    "integration_tests": subtask.get("test_plan", {}).get("integration_tests", []),
                    "edge_cases": subtask.get("test_plan", {}).get("edge_cases", []),
                    "performance_tests": subtask.get("test_plan", {}).get("performance_tests", []),
                    "test_data_requirements": subtask.get("test_plan", {}).get("test_data_requirements", [])
                } if subtask.get("test_plan") else None,
                "research_summary": {
                    "pain_points": subtask.get("research_summary", {}).get("pain_points", ""),
                    "success_metrics": subtask.get("research_summary", {}).get("success_metrics", ""),
                    "similar_implementations": subtask.get("research_summary", {}).get("similar_implementations", ""),
                    "modern_approaches": subtask.get("research_summary", {}).get("modern_approaches", ""),
                    "performance_considerations": subtask.get("research_summary", {}).get("performance_considerations", ""),
                    "security_implications": subtask.get("research_summary", {}).get("security_implications", ""),
                    "maintenance_aspects": subtask.get("research_summary", {}).get("maintenance_aspects", "")
                } if subtask.get("research_summary") else None
            })

        return subtask_ids

    def get_id_summary(self) -> Dict[str, int]:
        """Get summary of IDs generated for each type"""
        return {
            type_prefix: count
            for type_prefix, count in self.id_counters.items()
        }

    def save(self) -> None:
        """Save the proposed tickets to YAML file"""
        try:
            # Add ID counters to the YAML
            self.tickets_data["id_counters"] = self.get_id_summary()

            with open(self.filename, 'w') as f:
                yaml.safe_dump(
                    self.tickets_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )
            logger.info(f"Saved proposed tickets to {self.filename}")
            logger.debug(f"ID Summary: {self.get_id_summary()}")
        except Exception as e:
            logger.error(f"Failed to save proposed tickets: {str(e)}")

    def update_task_dependencies(self, task_id: str, resolved_dependencies: List[str]) -> None:
        """
        Update the dependencies of a task with resolved IDs.
        
        Args:
            task_id: ID of the task to update
            resolved_dependencies: List of resolved dependency IDs
        """
        # Find and update the task in high_level_tasks
        for task in self.tickets_data["user_stories"] + self.tickets_data["technical_tasks"]:
            if task.get("id") == task_id:
                task["dependencies"] = resolved_dependencies
                break
