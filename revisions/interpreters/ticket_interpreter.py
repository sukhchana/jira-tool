from typing import Dict, Any
from loguru import logger
import json
from .base_interpreter import BaseInterpreter
from ..models import DateTimeEncoder

class TicketInterpreter(BaseInterpreter):
    """Interpreter for ticket revision requests"""
    
    async def interpret_revision_request(
        self,
        ticket_data: Dict[str, Any],
        revision_request: str
    ) -> str:
        """Interpret a revision request for a ticket"""
        try:
            prompt = f"""
            Please interpret and structure the following revision request for a single JIRA ticket.
            
            Current Ticket:
            {json.dumps(ticket_data, indent=2, cls=DateTimeEncoder)}
            
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
            
            return await self.generate_interpretation(prompt)
            
        except Exception as e:
            logger.error(f"Failed to interpret ticket revision request: {str(e)}")
            logger.error(f"Ticket data: {json.dumps(ticket_data, cls=DateTimeEncoder)}")
            logger.error(f"Revision request: {revision_request}")
            raise 