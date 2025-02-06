from typing import Dict, Any, Optional, List
from uuid_extensions import uuid7
from loguru import logger
import json
from datetime import datetime
from llm.vertexllm import VertexLLM
from dataclasses import dataclass
from services.execution_log_service import ExecutionLogService
from services.mongodb_service import MongoDBService
from models.revision_request import RevisionRequest
from models.revision_record import RevisionRecord
import re

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

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
    
    def __init__(self):
        """Initialize the revision service"""
        self.mongodb = MongoDBService()
        self.llm = VertexLLM()
        self.execution_log = None
    
    def _ensure_execution_log(self, epic_key: str):
        """Ensure execution log is initialized with the correct epic key"""
        if not self.execution_log or self.execution_log.epic_key != epic_key:
            self.execution_log = ExecutionLogService(epic_key)
    
    async def create_revision(
        self,
        execution_id: str,
        ticket_id: str,
        changes_requested: str,
        changes_interpreted: str,
        epic_key: str
    ) -> RevisionRecord:
        """Create a new revision record"""
        try:
            revision_id = str(uuid7())
            
            # Initialize execution log
            self._ensure_execution_log(epic_key)
            
            revision = RevisionRecord(
                revision_id=revision_id,
                execution_id=execution_id,
                ticket_id=ticket_id,
                epic_key=epic_key,  # Store epic_key in the revision record
                proposed_plan_file="",  # No longer using files
                execution_plan_file=self.execution_log.filename,
                status="PENDING",
                created_at=datetime.now(),
                changes_requested=changes_requested,
                changes_interpreted=changes_interpreted
            )
            
            # Store revision in MongoDB
            revision_data = revision.model_dump()
            self.mongodb.create_revision(revision_data)
            
            # Log the revision details using the custom encoder
            self.execution_log.log_section(
                "Revision Details",
                json.dumps({
                    "revision_id": revision_id,
                    "execution_id": execution_id,
                    "ticket_id": ticket_id,
                    "epic_key": epic_key,
                    "changes_requested": changes_requested,
                    "changes_interpreted": changes_interpreted,
                    "status": "PENDING",
                    "created_at": datetime.now()
                }, indent=2, cls=DateTimeEncoder)
            )
            
            return revision
            
        except Exception as e:
            logger.error(f"Failed to create revision: {str(e)}")
            raise
    
    async def get_revision_record(self, revision_id: str) -> Optional[RevisionRecord]:
        """Get a revision record by ID"""
        revision_data = self.mongodb.get_revision(revision_id)
        if revision_data:
            return RevisionRecord(**revision_data)
        return None
    
    async def update_revision_status(
        self,
        revision_id: str,
        status: str,
        accepted: Optional[bool] = None
    ) -> None:
        """Update the status of a revision"""
        try:
            # Get the revision to get the epic_key
            revision = self.mongodb.get_revision(revision_id)
            if not revision:
                raise ValueError(f"Revision {revision_id} not found")
            
            # Initialize execution log with the epic key from the revision
            self._ensure_execution_log(revision.get("epic_key"))
            
            # Update in MongoDB
            updated = self.mongodb.update_revision_status(revision_id, status, accepted)
            if not updated:
                raise ValueError(f"Failed to update revision {revision_id}")
            
            # Log the status update
            self.execution_log.log_section(
                "Revision Status Update",
                json.dumps({
                    "revision_id": revision_id,
                    "status": status,
                    "accepted": accepted,
                    "updated_at": datetime.now()
                }, indent=2, cls=DateTimeEncoder)
            )
            
        except Exception as e:
            logger.error(f"Failed to update revision status: {str(e)}")
            raise

    async def interpret_revision_request(
        self,
        execution_id: str,
        ticket_id: str,
        revision_request: str
    ) -> str:
        """Have LLM interpret the revision request for a single ticket"""
        try:
            # Get the specific ticket from MongoDB
            target_ticket = self.mongodb.get_ticket_by_execution_and_id(execution_id, ticket_id)
            
            if not target_ticket:
                raise ValueError(f"Ticket {ticket_id} not found in execution {execution_id}")
            
            # Build the prompt with the single ticket
            prompt = f"""
            Please interpret and structure the following revision request for a single JIRA ticket.
            
            Current Ticket:
            {json.dumps(target_ticket.model_dump(), indent=2, cls=DateTimeEncoder)}
            
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
            - Fields to Modify: [List fields that need to be changed]
            - Dependencies Affected: [Yes/No, with details]
            - Related Tickets Impact: [List any related tickets that might be affected]
            
            Implementation Plan:
            [Step by step plan for implementing these changes]
            </interpretation>
            """
            
            # Get response
            response = await self.llm.generate_content(
                prompt,
                temperature=0.2,
                top_p=0.8,
                top_k=40
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to interpret revision request: {str(e)}")
            logger.error(f"Execution ID: {execution_id}")
            logger.error(f"Ticket ID: {ticket_id}")
            logger.error(f"Revision request: {revision_request}")
            raise

    async def apply_revision_changes(
        self,
        execution_id: str,
        ticket_id: str,
        changes_interpreted: str
    ) -> str:
        """Apply the interpreted changes to the ticket
        
        Args:
            execution_id: The execution ID of the ticket
            ticket_id: The ID of the ticket to update
            changes_interpreted: The LLM's interpretation of the changes to make
            
        Returns:
            str: Description of the changes that were made
        """
        try:
            # Get the ticket to modify
            target_ticket = self.mongodb.get_ticket_by_execution_and_id(execution_id, ticket_id)
            if not target_ticket:
                raise ValueError(f"Ticket {ticket_id} not found in execution {execution_id}")
            
            # Have LLM generate the actual changes
            prompt = f"""
            Please analyze the interpreted changes and generate the specific updates needed for this ticket.
            
            Current Ticket:
            {json.dumps(target_ticket.model_dump(), indent=2, cls=DateTimeEncoder)}
            
            Interpreted Changes:
            {changes_interpreted}
            
            Please provide the exact changes to make to the ticket in the following format:
            
            <changes>
            {{
                "field_updates": {{
                    "field_name": "new_value",
                    ...
                }},
                "list_append": {{
                    "field_name": ["value_to_append", ...],
                    ...
                }},
                "list_remove": {{
                    "field_name": ["value_to_remove", ...],
                    ...
                }},
                "changes_description": "A human-readable description of all changes made"
            }}
            </changes>
            
            Rules:
            1. Only include fields that need to be modified
            2. For list fields (like required_skills), specify whether to append or remove items
            3. Provide clear descriptions of changes in the changes_description
            4. Ensure all field names match the ticket model exactly
            5. Do not modify ticket_id, execution_id, or other metadata fields
            """
            
            # Get the changes from LLM
            changes_str = await self.llm.generate_content(
                prompt,
                temperature=0.2,
                top_p=0.8,
                top_k=40
            )
            
            # Extract the changes JSON
            changes_match = re.search(r'<changes>\s*(\{.*?\})\s*</changes>', changes_str, re.DOTALL)
            if not changes_match:
                raise ValueError("Could not extract changes JSON from LLM response")
                
            changes = json.loads(changes_match.group(1))
            
            # Apply field updates
            update_data = {}
            if "field_updates" in changes:
                update_data.update(changes["field_updates"])
            
            # Handle list append operations
            if "list_append" in changes:
                for field, values in changes["list_append"].items():
                    current_list = getattr(target_ticket, field, [])
                    if not isinstance(current_list, list):
                        current_list = []
                    update_data[field] = list(set(current_list + values))  # Remove duplicates
            
            # Handle list remove operations
            if "list_remove" in changes:
                for field, values in changes["list_remove"].items():
                    current_list = getattr(target_ticket, field, [])
                    if not isinstance(current_list, list):
                        continue
                    update_data[field] = [x for x in current_list if x not in values]
            
            # Update the ticket in MongoDB
            success = self.mongodb.update_ticket(execution_id, ticket_id, update_data)
            if not success:
                raise ValueError("Failed to update ticket in MongoDB")
            
            return changes.get("changes_description", "Changes applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply revision changes: {str(e)}")
            logger.error(f"Execution ID: {execution_id}")
            logger.error(f"Ticket ID: {ticket_id}")
            logger.error(f"Changes interpreted: {changes_interpreted}")
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