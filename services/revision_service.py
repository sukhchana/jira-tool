import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import yaml
from loguru import logger

from revisions.handlers import TicketHandler, ChangeHandler
from revisions.interpreters import TicketInterpreter, ChangeInterpreter
from revisions.managers import RevisionManager, StatusManager
from models.revision_record import RevisionRecord


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Handle MongoDB ObjectId
        try:
            from bson import ObjectId
            if isinstance(obj, ObjectId):
                return str(obj)
        except ImportError:
            pass
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
    """Service for handling ticket revisions"""

    def __init__(self):
        """Initialize the revision service with its components"""
        self.revision_manager = RevisionManager()
        self.status_manager = StatusManager()
        self.ticket_handler = TicketHandler()
        self.change_handler = ChangeHandler()
        self.ticket_interpreter = TicketInterpreter()
        self.change_interpreter = ChangeInterpreter()

    async def interpret_revision_request(
            self,
            execution_id: str,
            ticket_id: str,
            revision_request: str,
            epic_key: str = None
    ) -> str:
        """Interpret a revision request for a ticket"""
        try:
            # Get the ticket data
            ticket_data = await self.ticket_handler.get_ticket(execution_id, ticket_id, epic_key)
            if not ticket_data:
                raise ValueError(f"Ticket not found: {ticket_id}")

            # Delegate to the ticket interpreter
            return await self.ticket_interpreter.interpret_revision_request(
                ticket_data=ticket_data,
                revision_request=revision_request
            )
        except Exception as e:
            logger.error(f"Failed to interpret revision request: {str(e)}")
            raise

    async def create_revision(
            self,
            execution_id: str,
            ticket_id: str,
            changes_requested: str,
            changes_interpreted: str,
            epic_key: str
    ) -> Dict[str, Any]:
        """Create a new revision for a ticket"""
        try:
            # Get the ticket data
            ticket_data = await self.ticket_handler.get_ticket(execution_id, ticket_id, epic_key)
            if not ticket_data:
                raise ValueError(f"Ticket not found: {ticket_id}")

            # Create the revision
            revision = await self.revision_manager.create_revision(
                execution_id=execution_id,
                ticket_id=ticket_id,
                epic_key=epic_key,
                changes_requested=changes_requested
            )

            return revision

        except Exception as e:
            logger.error(f"Failed to create revision: {str(e)}")
            raise

    async def get_revision(self, revision_id: str) -> Optional[RevisionRecord]:
        """Get a revision by ID"""
        try:
            return await self.revision_manager.get_revision_record(revision_id)
        except Exception as e:
            logger.error(f"Failed to get revision: {str(e)}")
            raise

    async def update_revision_status(
            self,
            revision_id: str,
            status: str,
            accepted: Optional[bool] = None
    ) -> bool:
        """Update the status of a revision"""
        try:
            # Get the revision to get the epic_key
            revision = await self.get_revision(revision_id)
            if not revision:
                raise ValueError(f"Revision {revision_id} not found")

            # Access epic_key attribute directly instead of using dict .get() method
            epic_key = revision.epic_key
            if not epic_key:
                raise ValueError(f"Epic key not found in revision {revision_id}")

            return await self.status_manager.update_revision_status(
                revision_id=revision_id,
                status=status,
                accepted=accepted
            )
        except Exception as e:
            logger.error(f"Failed to update revision status: {str(e)}")
            raise

    async def apply_revision_changes(
            self,
            revision_id: str
    ) -> str:
        """Apply the changes from a revision to the ticket"""
        try:
            # Forward the call to the revision manager
            changes = await self.revision_manager.apply_revision_changes(revision_id)
            # Convert to JSON string for RevisionResponse
            return json.dumps(changes, cls=DateTimeEncoder, indent=2)
        except Exception as e:
            logger.error(f"Failed to apply revision changes: {str(e)}")
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
