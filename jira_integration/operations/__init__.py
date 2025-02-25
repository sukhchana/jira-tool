"""
JIRA operations module for direct REST API interactions.

This module provides specialized classes for different types of JIRA operations:

1. BaseJiraOperation: Base class for core REST API functionality, including 
   authentication and issue management.
2. EpicOperations: Operations specific to epics, such as retrieving epic details
   and creating epics.
3. TicketOperations: Operations for regular tickets, including creation and status updates.

All operations are implemented as asynchronous methods using aiohttp,
emphasizing efficient API interaction and robust error handling and logging.
"""

from jira_integration.operations.base_operation import BaseJiraOperation
from jira_integration.operations.epic_operations import EpicOperations
from jira_integration.operations.ticket_operations import TicketOperations

__all__ = ["BaseJiraOperation", "EpicOperations", "TicketOperations"]

# Import Pydantic models from the correct location
import sys
import os

# Make models available through jira_integration.models
# This helps maintain backward compatibility with existing code
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import models
    sys.modules['jira_integration.models'] = models
except ImportError:
    pass
