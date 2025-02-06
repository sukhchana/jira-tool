from typing import Dict, Any, Optional, List
from uuid_extensions import uuid7
from loguru import logger
import json
import os
from datetime import datetime
from llm.vertexllm import VertexLLM
from dataclasses import dataclass
import yaml
from services.execution_log_service import ExecutionLogService
from services.proposed_tickets_service import ProposedTicketsService
from models.revision_request import RevisionRequest
from models.revision_record import RevisionRecord

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
    """Service for handling revisions to epic breakdowns"""
    
    def __init__(self, epic_key: str):
        """Initialize the revision service"""
        self.epic_key = epic_key
        self.execution_log = ExecutionLogService(epic_key)
        self.proposed_tickets = ProposedTicketsService()
        self.llm = VertexLLM()
    
    async def create_revision(
        self,
        execution_id: str,
        changes_requested: str,
        changes_interpreted: str
    ) -> RevisionRecord:
        """Create a new revision record"""
        try:
            revision_id = str(uuid7())
            
            # Create new execution log and proposed tickets files for this revision
            self.execution_log = ExecutionLogService(self.epic_key)
            self.proposed_tickets = ProposedTicketsService()
            
            revision = RevisionRecord(
                revision_id=revision_id,
                execution_id=execution_id,
                proposed_plan_file=self.proposed_tickets.filename,
                execution_plan_file=self.execution_log.filename,
                status="PENDING",
                created_at=datetime.now(),
                changes_requested=changes_requested,
                changes_interpreted=changes_interpreted
            )
            
            # Log the revision details
            self.execution_log.log_section(
                "Revision Details",
                json.dumps({
                    "revision_id": revision_id,
                    "execution_id": execution_id,
                    "changes_requested": changes_requested,
                    "changes_interpreted": changes_interpreted,
                    "status": "PENDING"
                }, indent=2)
            )
            
            return revision
            
        except Exception as e:
            logger.error(f"Failed to create revision: {str(e)}")
            raise
    
    async def get_revision_record(self, revision_id: str) -> Optional[RevisionRecord]:
        """Get a revision record by ID"""
        # In the file-based system, we'll need to implement this differently
        # For now, return None as we don't have a way to look up old revisions
        return None
    
    async def update_revision_status(
        self,
        revision_id: str,
        status: str,
        accepted: Optional[bool] = None
    ) -> None:
        """Update the status of a revision"""
        try:
            # Log the status update
            self.execution_log.log_section(
                "Revision Status Update",
                json.dumps({
                    "revision_id": revision_id,
                    "status": status,
                    "accepted": accepted
                }, indent=2)
            )
            
        except Exception as e:
            logger.error(f"Failed to update revision status: {str(e)}")
            raise

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
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to interpret revision request: {str(e)}")
            logger.error(f"Execution ID: {execution_id}")
            logger.error(f"Revision request: {revision_request}")
            logger.error(f"Original tickets: {original_tickets if 'original_tickets' in locals() else 'Not loaded'}")
            raise

    async def _load_proposed_tickets(self, execution_id: str) -> Dict[str, Any]:
        """Load the proposed tickets YAML file for an execution"""
        try:
            # Since we don't have execution tracker anymore, we'll need to find the file directly
            # We'll look in the proposed_tickets directory for files containing the execution_id
            proposed_dir = "proposed_tickets"
            if not os.path.exists(proposed_dir):
                raise FileNotFoundError(f"Proposed tickets directory not found: {proposed_dir}")
            
            # Find the file containing the execution_id
            matching_files = []
            for filename in os.listdir(proposed_dir):
                if filename.endswith(".yaml"):
                    filepath = os.path.join(proposed_dir, filename)
                    with open(filepath, 'r') as f:
                        content = yaml.safe_load(f)
                        if content.get('execution_id') == execution_id:
                            matching_files.append(filepath)
            
            if not matching_files:
                raise FileNotFoundError(f"No proposed tickets file found for execution ID: {execution_id}")
            
            # Use the most recent file if multiple matches
            latest_file = max(matching_files, key=os.path.getctime)
            
            with open(latest_file, 'r') as f:
                tickets = yaml.safe_load(f)
                
            logger.debug(f"Loaded proposed tickets from {latest_file}")
            return tickets
            
        except Exception as e:
            logger.error(f"Failed to load proposed tickets for execution {execution_id}: {str(e)}")
            logger.error(f"Current working directory: {os.getcwd()}")
            raise 