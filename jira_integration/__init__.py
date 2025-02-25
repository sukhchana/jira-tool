"""
JIRA Integration Package

This package provides a complete integration with the JIRA REST API for managing
JIRA issues (epics, stories, tasks, and subtasks) using direct REST API calls 
via aiohttp.

Components:
- BaseJiraOperation: Base class for JIRA API operations
- EpicOperations: Operations specific to epics (create, update, query)
- TicketOperations: Operations for regular tickets (stories, tasks, subtasks)
- JiraService: High-level service combining various operations

Configuration:
Environment variables required for authentication and connection:
- JIRA_SERVER: The URL of the JIRA instance (e.g., https://your-domain.atlassian.net)
- JIRA_EMAIL: The email address for authentication
- JIRA_API_TOKEN: The API token for authentication
"""

from jira_integration.operations import BaseJiraOperation, EpicOperations, TicketOperations
from jira_integration.jira_service import JiraService
from jira_integration.jira_auth_helper import get_jira_auth_headers, get_jira_server

__all__ = [
    'BaseJiraOperation',
    'EpicOperations',
    'TicketOperations',
    'JiraService',
    'get_jira_auth_headers',
    'get_jira_server'
]

# Import Pydantic models from the correct location
import sys
import os

# Make models available through jira_integration.models
# This helps maintain backward compatibility with existing code
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import models
    sys.modules['jira_integration.models'] = models
except ImportError:
    pass
