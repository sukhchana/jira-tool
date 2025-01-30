from typing import Dict, Any, Optional
from uuid_extensions import uuid7
from loguru import logger
import json
import os
from datetime import datetime
from llm.vertexllm import VertexLLM
from dataclasses import dataclass
import yaml
from services.execution_tracker_service import ExecutionTrackerService
from services.execution_tracker_service import ExecutionRecord
import sqlite3
import re
from config.database import DATABASE

@dataclass
class RevisionDetails:
    revision_id: str
    execution_id: str
    interpreted_changes: str
    changes_requested: str
    proposed_plan_file: str
    execution_plan_file: str
    status: str
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None

class RevisionService:
    """Service for handling execution plan revisions"""
    
    def __init__(self):
        """Initialize the revision service"""
        self.llm = VertexLLM()
        self.temp_dir = "temp_revisions"
        self.execution_tracker = ExecutionTrackerService()
        self.db_file = DATABASE["sqlite"]["path"]  # Add database path from config
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def interpret_revision_request(
        self,
        execution_id: str,
        revision_request: str
    ) -> str:
        """Have LLM interpret the revision request"""
        try:
            # Add debug logging to see what we're loading
            logger.debug(f"Loading proposed tickets for execution: {execution_id}")
            
            # Load the original proposed tickets
            original_tickets = await self._load_proposed_tickets(execution_id)
            logger.debug(f"Loaded tickets: {original_tickets}")
            
            # Build the prompt with more context
            prompt = f"""
            Please interpret and structure the following revision request for a JIRA ticket structure.
            
            Current Ticket Structure:
            {yaml.dump(original_tickets, sort_keys=False)}
            
            User's Revision Request:
            {revision_request}
            
            Please analyze the request and provide a clear, structured interpretation of the changes needed.
            Format your response as follows:

            <interpretation>
            Requested Changes:
            1. [First change requested]
            2. [Second change requested]
            ...

            Impact Analysis:
            - Tasks Affected: [List affected tasks]
            - New Tasks Required: [Yes/No, with details]
            - Dependencies Modified: [Yes/No, with details]
            
            Implementation Plan:
            [Step by step plan for implementing these changes]
            </interpretation>
            """
            
            # Log the prompt for debugging
            logger.debug(f"Generated prompt: {prompt}")
            
            # Get response - already returns text string
            response = await self.llm.generate_content(
                prompt,
                temperature=0.2,
                top_p=0.8,
                top_k=40
            )
            
            # Log the response
            logger.debug(f"LLM Response: {response}")
            
            # Return the response directly since it's already text
            return response
            
        except Exception as e:
            logger.error(f"Failed to interpret revision request: {str(e)}")
            logger.error(f"Execution ID: {execution_id}")
            logger.error(f"Revision request: {revision_request}")
            logger.error(f"Original tickets: {original_tickets if 'original_tickets' in locals() else 'Not loaded'}")
            raise

    async def store_revision_request(
        self,
        temp_revision_id: str,
        original_execution_id: str,
        interpreted_changes: str,
        epic_key: str
    ) -> None:
        """Store the revision request for later confirmation"""
        temp_file = os.path.join(self.temp_dir, f"{temp_revision_id}.json")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate filenames for both execution and proposed plans
        execution_plan_file = f"execution_plans/EXECUTION_{epic_key}_{timestamp}.md"
        proposed_plan_file = f"proposed_tickets/PROPOSED_{epic_key}_{timestamp}.yaml"
        
        await self.execution_tracker.create_revision_record(
            revision_id=temp_revision_id,
            execution_id=original_execution_id,
            changes_requested=interpreted_changes,
            changes_interpreted=interpreted_changes,
            proposed_plan_file=proposed_plan_file,
            execution_plan_file=execution_plan_file
        )

    async def get_revision_details(self, temp_revision_id: str) -> RevisionDetails:
        """Get stored revision details"""
        try:
            # Get revision from database
            revision = await self.execution_tracker.get_revision_record(temp_revision_id)
            
            return RevisionDetails(
                revision_id=revision.revision_id,
                execution_id=revision.execution_id,
                interpreted_changes=revision.changes_interpreted,
                changes_requested=revision.changes_requested,
                proposed_plan_file=revision.proposed_plan_file,
                execution_plan_file=revision.execution_plan_file,
                status=revision.status,
                accepted=revision.accepted,
                accepted_at=revision.accepted_at
            )
        except Exception as e:
            logger.error(f"Failed to get revision details: {str(e)}")
            logger.error(f"Revision ID: {temp_revision_id}")
            raise ValueError(f"No revision found for ID: {temp_revision_id}")

    async def apply_revision(
        self,
        original_execution_id: str,
        interpreted_changes: str,
        new_execution_id: str
    ) -> ExecutionRecord:
        """Apply the confirmed changes and generate new execution plan"""
        try:
            # Get original execution details
            original_execution = await self.execution_tracker.get_execution_record(
                original_execution_id
            )
            
            # Generate new filenames with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_execution_file = f"execution_plans/EXECUTION_{original_execution.epic_key}_{timestamp}.md"
            new_proposed_file = f"proposed_tickets/PROPOSED_{original_execution.epic_key}_{timestamp}.yaml"
            
            # Load original proposed tickets
            with open(original_execution.proposed_plan_file, 'r') as f:
                original_tickets = yaml.safe_load(f)
                
            # Build prompt for LLM to apply changes
            prompt = f"""
            Please update the following JIRA ticket structure based on the requested changes.
            
            Current Ticket Structure:
            {yaml.dump(original_tickets, sort_keys=False)}
            
            Requested Changes:
            {interpreted_changes}
            
            Please provide an updated YAML structure that:
            1. Incorporates the requested changes
            2. Includes these metadata fields at the top of the YAML:
               - execution_id: {new_execution_id}
               - parent_execution_id: {original_execution_id}
               - epic_key: {original_execution.epic_key}
               - timestamp: {datetime.now().isoformat()}
            3. Maintains the same structure for tasks and subtasks
            
            Also provide a markdown execution plan explaining the changes and implementation steps.
            
            Format your response exactly as follows:
            
            <yaml>
            execution_id: {new_execution_id}
            parent_execution_id: {original_execution_id}
            epic_key: {original_execution.epic_key}
            timestamp: {datetime.now().isoformat()}
            
            [Rest of the updated YAML structure here...]
            </yaml>
            
            <execution_plan>
            [Updated markdown execution plan here]
            </execution_plan>
            """
            
            # Get response - already returns text string
            response = await self.llm.generate_content(
                prompt,
                temperature=0.2,
                top_p=0.8,
                top_k=40
            )
            
            # Extract YAML and execution plan from response directly (it's already text)
            yaml_match = re.search(r'<yaml>(.*?)</yaml>', response, re.DOTALL)
            plan_match = re.search(r'<execution_plan>(.*?)</execution_plan>', response, re.DOTALL)
            
            if not yaml_match or not plan_match:
                raise ValueError("Failed to get valid response from LLM")
            
            # Validate YAML structure has required fields
            yaml_content = yaml_match.group(1).strip()
            proposed_tickets = yaml.safe_load(yaml_content)
            
            required_fields = ['execution_id', 'parent_execution_id', 'epic_key', 'timestamp']
            missing_fields = [field for field in required_fields if field not in proposed_tickets]
            if missing_fields:
                raise ValueError(f"LLM response missing required fields: {', '.join(missing_fields)}")
                
            # Save new proposed tickets YAML
            os.makedirs(os.path.dirname(new_proposed_file), exist_ok=True)
            with open(new_proposed_file, 'w') as f:
                f.write(yaml_content)
                
            # Save new execution plan
            os.makedirs(os.path.dirname(new_execution_file), exist_ok=True)
            with open(new_execution_file, 'w') as f:
                f.write(plan_match.group(1).strip())
                
            # Create new execution record with link to parent
            new_execution = await self.execution_tracker.create_execution_record(
                execution_id=new_execution_id,
                epic_key=original_execution.epic_key,
                execution_plan_file=new_execution_file,
                proposed_plan_file=new_proposed_file,
                parent_execution_id=original_execution_id
            )
            
            # Update revision status to APPLIED
            await self.execution_tracker.update_revision_status(
                revision_id=new_execution_id,
                status="APPLIED"
            )
            
            return new_execution
            
        except Exception as e:
            logger.error(f"Failed to apply revision: {str(e)}")
            logger.error(f"Original execution ID: {original_execution_id}")
            logger.error(f"Changes requested:\n{interpreted_changes}")
            raise

    async def _load_proposed_tickets(self, execution_id: str) -> Dict[str, Any]:
        """Load the proposed tickets YAML file for an execution"""
        try:
            # Get execution record to find the file
            logger.debug(f"Getting execution record for: {execution_id}")
            execution = await self.execution_tracker.get_execution_record(execution_id)
            
            # Log the file path
            logger.debug(f"Looking for proposed tickets file: {execution.proposed_plan_file}")
            
            # Load and parse YAML file
            if not os.path.exists(execution.proposed_plan_file):
                raise FileNotFoundError(f"Proposed tickets file not found: {execution.proposed_plan_file}")
                
            with open(execution.proposed_plan_file, 'r') as f:
                tickets = yaml.safe_load(f)
                
            logger.debug(f"Loaded proposed tickets for execution {execution_id}: {tickets}")
            return tickets
            
        except Exception as e:
            logger.error(f"Failed to load proposed tickets for execution {execution_id}: {str(e)}")
            logger.error(f"Current working directory: {os.getcwd()}")
            raise

    async def confirm_revision_request(
        self,
        temp_revision_id: str,
        accepted: bool
    ) -> ExecutionRecord:
        """Record the user's confirmation of the interpreted changes"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE revisions 
                    SET status = ?, 
                        accepted = ?,
                        accepted_at = ?
                    WHERE revision_id = ?
                """, (
                    "ACCEPTED" if accepted else "REJECTED",
                    accepted,
                    datetime.now().isoformat() if accepted else None,
                    temp_revision_id
                ))
                conn.commit()
            
            return await self.execution_tracker.get_revision_record(temp_revision_id)
            
        except Exception as e:
            logger.error(f"Failed to confirm revision request: {str(e)}")
            raise 