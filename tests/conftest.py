import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

# Add the root directory to the path to ensure models can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the models we'll need in tests
from models.jira_ticket_creation import JiraTicketCreation
from models.jira_ticket_details import JiraTicketDetails
from models.jira_linked_ticket import JiraLinkedTicket
from models.jira_epic_details import JiraEpicDetails
from models.jira_epic_progress import JiraEpicProgress

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

# Remove the custom event_loop fixture as it's deprecated
# and instead use the built-in one from pytest-asyncio
# The loop scope is now configured in pytest.ini 

@pytest.fixture
def mock_response():
    """Create a mock aiohttp response object."""
    mock = AsyncMock()
    mock.status = 200
    mock.json = AsyncMock(return_value={})
    return mock


@pytest.fixture
def mock_aiohttp_client():
    """Create a mock aiohttp ClientSession."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock()
    mock_client.get = AsyncMock()
    mock_client.put = AsyncMock()
    return mock_client


@pytest.fixture
def mock_env_vars():
    """Mock environment variables needed for JIRA authentication."""
    with patch.dict(os.environ, {
        "JIRA_SERVER": "https://jira.example.com",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    }):
        yield 