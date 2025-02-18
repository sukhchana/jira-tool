from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from uuid_extensions import uuid7
import json

from services.mongodb_service import MongoDBService
from services.execution_log_service import ExecutionLogService
from models.revision_record import RevisionRecord
from ..models import DateTimeEncoder
from ..interpreters import TicketInterpreter, ChangeInterpreter

class RevisionManager:
    """Manager for handling the revision lifecycle"""
    
    def __init__(self):
        """Initialize the revision manager"""
        self.mongodb = MongoDBService()
        self.ticket_interpreter = TicketInterpreter()
        self.change_interpreter = ChangeInterpreter()
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
        epic_key: str
    ) -> RevisionRecord:
        """Create a new revision record"""
        try:
            # Initialize execution log
            self._ensure_execution_log(epic_key)
            
            # Get the ticket data
            ticket_data = self.mongodb.get_ticket_by_execution_and_id(execution_id, ticket_id)
            if not ticket_data:
                raise ValueError(f"Ticket {ticket_id} not found in execution {execution_id}")
            
            # Interpret the changes
            interpreted_changes = await self.ticket_interpreter.interpret_revision_request(
                ticket_data.model_dump(),
                changes_requested
            )
            
            # Create revision record
            revision_id = str(uuid7())
            revision = RevisionRecord(
                revision_id=revision_id,
                execution_id=execution_id,
                ticket_id=ticket_id,
                epic_key=epic_key,
                proposed_plan_file="",
                execution_plan_file=self.execution_log.filename,
                status="PENDING",
                created_at=datetime.now(),
                changes_requested=changes_requested,
                changes_interpreted=interpreted_changes
            )
            
            # Store revision in MongoDB
            revision_data = revision.model_dump()
            self.mongodb.create_revision(revision_data)
            
            # Log the revision details
            self.execution_log.log_section(
                "Revision Details",
                json.dumps(revision_data, indent=2, cls=DateTimeEncoder)
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
    
    async def apply_revision_changes(
        self,
        revision_id: str
    ) -> Dict[str, Any]:
        """Apply the changes from a revision"""
        try:
            # Get the revision record
            revision = await self.get_revision_record(revision_id)
            if not revision:
                raise ValueError(f"Revision {revision_id} not found")
            
            # Get the ticket data
            ticket_data = self.mongodb.get_ticket_by_execution_and_id(
                revision.execution_id,
                revision.ticket_id
            )
            if not ticket_data:
                raise ValueError(f"Ticket {revision.ticket_id} not found")
            
            # Generate specific changes
            changes = await self.change_interpreter.generate_changes(
                ticket_data.model_dump(),
                revision.changes_interpreted
            )
            
            # Apply the changes
            update_data = {}
            
            # Apply direct field updates
            update_data.update(changes["field_updates"])
            
            # Handle list append operations
            for field, values in changes["list_append"].items():
                current = ticket_data.model_dump().get(field, [])
                if not isinstance(current, list):
                    current = []
                update_data[field] = list(set(current + values))
            
            # Handle list remove operations
            for field, values in changes["list_remove"].items():
                current = ticket_data.model_dump().get(field, [])
                if not isinstance(current, list):
                    continue
                update_data[field] = [v for v in current if v not in values]
            
            # Update the ticket
            success = self.mongodb.update_ticket(
                revision.execution_id,
                revision.ticket_id,
                update_data
            )
            
            if not success:
                raise ValueError("Failed to update ticket")
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to apply revision changes: {str(e)}")
            raise 