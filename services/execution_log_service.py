import os
from datetime import datetime
from typing import Dict, Any
from loguru import logger
import json
from uuid_extensions import uuid7  # Correct import for uuid7


class ExecutionLogService:
    """Service for logging execution details to markdown files"""
    
    def __init__(self, epic_key: str):
        """Initialize with epic key to create unique log file"""
        self.epic_key = epic_key
        self.execution_id = str(uuid7())  # Generate UUID-7
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = f"execution_plans/EXECUTION_{epic_key}_{self.timestamp}.md"
        
        # Ensure execution_plans directory exists
        os.makedirs("execution_plans", exist_ok=True)
        
        # Initialize the file with header
        with open(self.filename, "w") as f:
            f.write(f"# EXECUTION_PLAN_ID: {self.execution_id}\n\n")
            f.write(f"## Epic: {epic_key}\n")
            f.write(f"## Started: {datetime.now().isoformat()}\n\n")
    
    def log_section(self, title: str, content: str):
        """Log a new section to the execution plan"""
        try:
            with open(self.filename, "a") as f:
                f.write(f"\n## {title}\n\n")
                # Check if content is JSON-serializable
                try:
                    json_obj = json.loads(content) if isinstance(content, str) else content
                    f.write(f"```json\n{json.dumps(json_obj, indent=2)}\n```\n")
                except (json.JSONDecodeError, TypeError):
                    f.write(f"```\n{content}\n```\n")
        except Exception as e:
            logger.error(f"Failed to log section to execution plan: {str(e)}")
    
    def log_llm_interaction(self, stage: str, prompt: str, response: str, parsed_result: Dict[str, Any] = None):
        """Log an LLM interaction including prompt, response, and parsed results"""
        try:
            with open(self.filename, "a") as f:
                f.write(f"\n## {stage}\n\n")
                
                f.write("### Prompt\n")
                f.write(f"```\n{prompt}\n```\n\n")
                
                f.write("### Raw Response\n")
                f.write(f"```\n{response}\n```\n\n")
                
                if parsed_result:
                    f.write("### Parsed Result\n")
                    f.write("```json\n")  # Specify json language for formatting
                    f.write(f"{json.dumps(parsed_result, indent=2)}\n")
                    f.write("```\n")
        except Exception as e:
            logger.error(f"Failed to log LLM interaction to execution plan: {str(e)}")
    
    def log_summary(self, summary: Dict[str, Any]):
        """Log final summary of the execution"""
        try:
            with open(self.filename, "a") as f:
                f.write("\n## Execution Summary\n\n")
                f.write("### Statistics\n")
                f.write(f"- Total User Stories: {summary.get('user_stories', 0)}\n")
                f.write(f"- Total Technical Tasks: {summary.get('technical_tasks', 0)}\n")
                f.write(f"- Total Subtasks: {summary.get('subtasks', 0)}\n\n")
                
                if 'errors' in summary and summary['errors']:
                    f.write("### Errors\n")
                    for error in summary['errors']:
                        f.write(f"- {error}\n")
        except Exception as e:
            logger.error(f"Failed to log summary to execution plan: {str(e)}") 