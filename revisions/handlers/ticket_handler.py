from typing import Dict, Any, Optional
from loguru import logger

from services.mongodb_service import MongoDBService
from services.execution_log_service import ExecutionLogService
from ..models import DateTimeEncoder
import json

class TicketHandler:
    """Handler for ticket operations"""
    
    def __init__(self):
        """Initialize the ticket handler"""
        self.mongodb = MongoDBService()
        self.execution_log = None
    
    def _ensure_execution_log(self, epic_key: str):
        """Ensure execution log is initialized with the correct epic key"""
        if not self.execution_log or self.execution_log.epic_key != epic_key:
            self.execution_log = ExecutionLogService(epic_key)
    
    async def get_ticket(
        self,
        execution_id: str,
        ticket_id: str,
        epic_key: str
    ) -> Optional[Dict[str, Any]]:
        """Get a ticket by ID"""
        try:
            # Initialize execution log
            self._ensure_execution_log(epic_key)
            
            # Get the ticket
            ticket_data = self.mongodb.get_ticket_by_execution_and_id(execution_id, ticket_id)
            if not ticket_data:
                return None
            
            # Log the retrieval
            self.execution_log.log_section(
                "Ticket Retrieved",
                json.dumps({
                    "ticket_id": ticket_id,
                    "execution_id": execution_id,
                    "epic_key": epic_key
                }, indent=2, cls=DateTimeEncoder)
            )
            
            return ticket_data.model_dump()
            
        except Exception as e:
            logger.error(f"Failed to get ticket: {str(e)}")
            raise
    
    async def update_ticket(
        self,
        execution_id: str,
        ticket_id: str,
        update_data: Dict[str, Any],
        epic_key: str
    ) -> bool:
        """Update a ticket"""
        try:
            # Initialize execution log
            self._ensure_execution_log(epic_key)
            
            # Update the ticket
            success = self.mongodb.update_ticket(execution_id, ticket_id, update_data)
            
            # Log the update
            self.execution_log.log_section(
                "Ticket Updated",
                json.dumps({
                    "ticket_id": ticket_id,
                    "execution_id": execution_id,
                    "epic_key": epic_key,
                    "update_data": update_data,
                    "success": success
                }, indent=2, cls=DateTimeEncoder)
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update ticket: {str(e)}")
            logger.error(f"Update data: {json.dumps(update_data, cls=DateTimeEncoder)}")
            raise 