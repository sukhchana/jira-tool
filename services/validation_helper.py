from typing import Dict, Any, List
from loguru import logger

class ValidationHelper:
    """Helper class for validating task structures and data"""
    
    @staticmethod
    def validate_task_structure(task: Dict[str, Any], task_type: str) -> bool:
        """Validate a high-level task has all required fields"""
        required_fields = {
            "type": str,
            "name": str,
            "description": str,
            "technical_domain": str,
            "complexity": str,
            "dependencies": list
        }
        
        # Add type-specific required fields
        if task_type == "User Story":
            required_fields["business_value"] = str
        elif task_type == "Technical Task":
            required_fields["implementation_notes"] = str
            
        try:
            for field, field_type in required_fields.items():
                if field not in task:
                    logger.error(f"Missing required field '{field}' in {task_type}")
                    return False
                if not isinstance(task[field], field_type):
                    logger.error(f"Field '{field}' in {task_type} has wrong type. Expected {field_type}, got {type(task[field])}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error validating {task_type} structure: {str(e)}")
            return False

    @staticmethod
    def validate_subtask_structure(subtask: Dict[str, Any]) -> bool:
        """Validate a subtask has all required fields"""
        required_fields = {
            "title": str,
            "description": str,
            "acceptance_criteria": str,
            "story_points": int,
            "required_skills": list,
            "dependencies": list,
            "suggested_assignee": str
        }
        
        try:
            for field, field_type in required_fields.items():
                if field not in subtask:
                    logger.error(f"Missing required field '{field}' in subtask")
                    return False
                if not isinstance(subtask[field], field_type):
                    logger.error(f"Field '{field}' in subtask has wrong type. Expected {field_type}, got {type(subtask[field])}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error validating subtask structure: {str(e)}")
            return False

    @staticmethod
    def validate_task_group(task_group: Dict[str, Any]) -> bool:
        """Validate a task group (high-level task + subtasks) structure"""
        try:
            if "high_level_task" not in task_group:
                logger.error("Missing 'high_level_task' in task group")
                return False
            
            if "subtasks" not in task_group:
                logger.error("Missing 'subtasks' in task group")
                return False
                
            if not isinstance(task_group["subtasks"], list):
                logger.error("'subtasks' must be a list")
                return False
                
            task_type = task_group["high_level_task"].get("type")
            if not ValidationHelper.validate_task_structure(task_group["high_level_task"], task_type):
                return False
                
            for subtask in task_group["subtasks"]:
                if not ValidationHelper.validate_subtask_structure(subtask):
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error validating task group: {str(e)}")
            return False 