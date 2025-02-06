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
from services.proposed_tickets_service import ProposedTicketsService

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
        self.proposed_tickets = ProposedTicketsService()
        self.db_file = DATABASE["sqlite"]["path"]  # Add database path from config
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def interpret_revision_request(
        self,
        execution_id: str,
        high_level_task_id: str,
        revision_request: str
    ) -> str:
        """Have LLM interpret the revision request for a specific user story"""
        try:
            logger.debug(f"Loading proposed tickets for execution: {execution_id}")
            
            # Load all tickets but extract only the requested task and its subtasks
            all_tickets = await self._load_proposed_tickets(execution_id)
            
            # Find the specific task and its subtasks
            target_task = None
            for task in all_tickets:
                if task.get("id") == high_level_task_id:
                    target_task = task
                    break
                    
            if not target_task:
                raise ValueError(f"No task found with ID {high_level_task_id}")
            
            # Build the prompt with focused context
            prompt = f"""
            Please interpret and structure the following revision request for a specific JIRA user story/task.
            
            Current Task Structure:
            {yaml.dump(target_task, sort_keys=False)}
            
            User's Revision Request:
            {revision_request}
            
            Please analyze the request and provide a clear, structured interpretation of the changes needed.
            Focus only on changes to this specific task and its subtasks.
            
            Format your response as follows:

            <interpretation>
            Requested Changes:
            1. [First change requested]
            2. [Second change requested]
            ...

            Impact Analysis:
            - Task Components Affected: [List affected components of this task]
            - Subtasks Modified: [List affected subtasks]
            - New Subtasks Required: [Yes/No, with details]
            - Dependencies Modified: [Yes/No, with details]
            
            Implementation Plan:
            [Step by step plan for implementing these changes]
            </interpretation>
            """
            
            # Get LLM response
            response = await self.llm.generate_content(
                prompt,
                temperature=0.2,
                top_p=0.8,
                top_k=40
            )
            
            logger.debug(f"LLM Response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to interpret revision request: {str(e)}")
            logger.error(f"Execution ID: {execution_id}")
            logger.error(f"Task ID: {high_level_task_id}")
            logger.error(f"Revision request: {revision_request}")
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
            
            # Load original proposed tickets
            original_tickets = await self._load_proposed_tickets(original_execution_id)
            
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
            
            # Parse the updated tickets
            yaml_content = yaml_match.group(1).strip()
            proposed_tickets = yaml.safe_load(yaml_content)
            
            # Store the new proposal in database
            new_proposal_id = await self.proposed_tickets.store_proposal(
                execution_id=new_execution_id,
                epic_key=original_execution.epic_key,
                high_level_tasks=proposed_tickets["tasks"],  # Adjust based on your YAML structure
                parent_proposal_id=original_execution_id  # Link to parent
            )
            
            logger.debug(f"Stored new proposal {new_proposal_id} for execution {new_execution_id}")
            
            # Create new execution record
            new_execution = await self.execution_tracker.create_execution_record(
                execution_id=new_execution_id,
                epic_key=original_execution.epic_key,
                execution_plan_file=plan_match.group(1).strip(),
                proposed_plan_file=yaml_content,
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
        """Load the proposed tickets from database"""
        return await self.proposed_tickets.get_proposal_by_execution(execution_id)

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