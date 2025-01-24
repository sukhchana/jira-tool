from datetime import datetime
import os
import yaml
from typing import Dict, Any, List
from loguru import logger

class ProposedTicketsService:
    """Service for tracking proposed JIRA tickets in YAML format"""
    
    def __init__(self, epic_key: str, execution_id: str):
        """Initialize with epic key and execution ID"""
        self.epic_key = epic_key
        self.execution_id = execution_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = f"proposed_tickets/PROPOSED_{epic_key}_{timestamp}.yaml"
        
        # Initialize ID counters
        self.id_counters = {
            "USER-STORY": 0,
            "TECHNICAL-TASK": 0,
            "SUB-TASK": 0,
            "SCENARIO": 0  # Add counter for scenarios
        }
        
        # Ensure directory exists
        os.makedirs("proposed_tickets", exist_ok=True)
        
        # Initialize the YAML structure
        self.tickets_data = {
            "execution_id": execution_id,
            "epic_key": epic_key,
            "timestamp": datetime.now().isoformat(),
            "high_level_tasks": [],
            "subtasks": {}
        }
    
    def _generate_id(self, type_prefix: str) -> str:
        """Generate a sequential ID for a given type"""
        self.id_counters[type_prefix] += 1
        return f"{type_prefix}-{self.id_counters[type_prefix]}"
    
    def add_high_level_task(self, task: Dict[str, Any]) -> None:
        """Add a high-level task (user story or technical task)"""
        # Determine task type and generate ID
        type_prefix = "USER-STORY" if task["type"] == "User Story" else "TECHNICAL-TASK"
        task_id = self._generate_id(type_prefix)
        
        task_data = {
            "id": task_id,
            "type": task["type"],
            "name": task["name"],
            "description": task["description"],
            "technical_domain": task["technical_domain"],
            "complexity": task["complexity"],
            "dependencies": task["dependencies"],
            "business_value": task.get("business_value"),
            "implementation_notes": task.get("implementation_notes")
        }
        
        # Add scenarios for user stories with IDs
        if task["type"] == "User Story" and "scenarios" in task:
            task_data["scenarios"] = [
                {
                    "id": self._generate_id("SCENARIO"),
                    "name": scenario["name"],
                    "steps": scenario["steps"]
                }
                for scenario in task["scenarios"]
            ]
        
        self.tickets_data["high_level_tasks"].append(task_data)
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
                "suggested_assignee": subtask["suggested_assignee"]
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