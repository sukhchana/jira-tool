import json
from typing import Dict, Any

from loguru import logger

from services.execution_log_service import ExecutionLogService
from services.mongodb_service import MongoDBService
from ..models import DateTimeEncoder


class ChangeHandler:
    """Handler for applying changes to tickets"""

    def __init__(self):
        """Initialize the change handler"""
        self.mongodb = MongoDBService()
        self.execution_log = None

    def _ensure_execution_log(self, epic_key: str):
        """Ensure execution log is initialized with the correct epic key"""
        if not self.execution_log or self.execution_log.epic_key != epic_key:
            self.execution_log = ExecutionLogService(epic_key)

    async def apply_changes(
            self,
            execution_id: str,
            ticket_id: str,
            changes: Dict[str, Any],
            epic_key: str
    ) -> bool:
        """Apply changes to a ticket"""
        try:
            # Initialize execution log
            self._ensure_execution_log(epic_key)

            # Get current ticket data
            ticket_data = self.mongodb.get_ticket_by_execution_and_id(execution_id, ticket_id)
            if not ticket_data:
                raise ValueError(f"Ticket {ticket_id} not found")

            # Prepare update data using shared method
            update_data = self.mongodb.prepare_ticket_update(ticket_data, changes)

            # Update the ticket
            success = self.mongodb.update_ticket(execution_id, ticket_id, update_data)

            # Log the changes
            self.execution_log.log_section(
                "Applied Changes",
                json.dumps({
                    "ticket_id": ticket_id,
                    "changes": changes,
                    "success": success
                }, indent=2, cls=DateTimeEncoder)
            )

            return success

        except Exception as e:
            logger.error(f"Failed to apply changes: {str(e)}")
            logger.error(f"Changes: {json.dumps(changes, cls=DateTimeEncoder)}")
            raise
