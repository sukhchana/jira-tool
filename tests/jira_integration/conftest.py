import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from pytest_mock import MockerFixture
from http import HTTPStatus
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set test environment variables (if needed, can be removed if all are in .env)
os.environ.setdefault("JIRA_SERVER", "https://test-jira.example.com")
os.environ.setdefault("JIRA_EMAIL", "test@example.com")
os.environ.setdefault("JIRA_API_TOKEN", "test-token-123")


@pytest.fixture
def mock_response():
    """Create a mock response with custom status and json content."""
    def _create_mock_response(status=HTTPStatus.OK, json_data=None, text=""):
        mock_resp = AsyncMock()
        mock_resp.status = status
        mock_resp.json = AsyncMock(return_value=json_data or {})
        mock_resp.text = AsyncMock(return_value=text)
        return mock_resp
    return _create_mock_response


@pytest.fixture
def mock_aiohttp_session(mocker: MockerFixture, mock_response):
    """Mock aiohttp.ClientSession for HTTP requests."""
    # Create the main session mock
    session_mock = AsyncMock(spec=aiohttp.ClientSession)
    
    # Create response mocks for different HTTP methods
    get_context_mock = AsyncMock()
    post_context_mock = AsyncMock()
    put_context_mock = AsyncMock()
    delete_context_mock = AsyncMock()
    
    # Configure the session methods to return their respective context managers
    session_mock.get.return_value = get_context_mock
    session_mock.post.return_value = post_context_mock
    session_mock.put.return_value = put_context_mock
    session_mock.delete.return_value = delete_context_mock
    
    # By default, the context managers will return a generic OK response
    # These can be overridden in individual tests
    default_response = mock_response(status=HTTPStatus.OK)
    get_context_mock.__aenter__.return_value = default_response
    post_context_mock.__aenter__.return_value = default_response
    put_context_mock.__aenter__.return_value = default_response
    delete_context_mock.__aenter__.return_value = default_response
    
    # Make sure the exit methods return None to avoid issues
    get_context_mock.__aexit__.return_value = None
    post_context_mock.__aexit__.return_value = None
    put_context_mock.__aexit__.return_value = None
    delete_context_mock.__aexit__.return_value = None
    
    # Patch aiohttp.ClientSession to return our mock
    with patch('aiohttp.ClientSession', return_value=session_mock):
        yield session_mock


@pytest.fixture
def mock_jira_auth_headers(mocker: MockerFixture):
    """Mock the get_jira_auth_headers function."""
    mocker.patch('jira_integration.jira_auth_helper.get_jira_auth_headers', 
                return_value="Basic dGVzdEBleGFtcGxlLmNvbTp0ZXN0LXRva2VuLTEyMw==")
    return "Basic dGVzdEBleGFtcGxlLmNvbTp0ZXN0LXRva2VuLTEyMw=="


@pytest.fixture
def base_issue_response():
    """Fixture for a basic JIRA issue response."""
    return {
        "key": "TEST-123",
        "fields": {
            "summary": "Test Issue",
            "description": "Test Description",
            "status": {"name": "To Do"},
            "issuetype": {"name": "Story"},
            "project": {"key": "TEST"},
            "created": "2023-01-01T12:00:00.000+0000",
            "updated": "2023-01-02T12:00:00.000+0000",
            "assignee": {"displayName": "Test User"},
            "reporter": {"displayName": "Reporter User"},
            "priority": {"name": "Medium"},
            "labels": ["label1", "label2"],
            "components": [{"name": "Component1"}, {"name": "Component2"}]
        }
    }


@pytest.fixture
def epic_issue_response(base_issue_response):
    """Fixture for a JIRA epic response."""
    response = base_issue_response.copy()
    response["fields"]["issuetype"]["name"] = "Epic"
    response["key"] = "TEST-E123"  # Using E prefix for epics
    return response


@pytest.fixture
def epic_linked_issues_response():
    """Fixture for issues linked to an epic."""
    return {
        "issues": [
            {
                "key": "TEST-124",
                "fields": {
                    "summary": "Linked Story",
                    "description": "Description",
                    "issuetype": {"name": "Story"},
                    "status": {"name": "In Progress"},
                    "project": {"key": "TEST"},
                    "created": "2023-01-01T12:00:00.000+0000",
                    "updated": "2023-01-02T12:00:00.000+0000"
                }
            },
            {
                "key": "TEST-125",
                "fields": {
                    "summary": "Linked Task",
                    "description": "Description",
                    "issuetype": {"name": "Task"},
                    "status": {"name": "Done"},
                    "project": {"key": "TEST"},
                    "created": "2023-01-01T12:00:00.000+0000",
                    "updated": "2023-01-02T12:00:00.000+0000"
                }
            }
        ]
    }


@pytest.fixture
def issue_links_response():
    """Fixture for issue links response."""
    return {
        "fields": {
            "issuelinks": [
                {
                    "type": {
                        "name": "Blocks",
                        "inward": "is blocked by",
                        "outward": "blocks"
                    },
                    "outwardIssue": {
                        "key": "TEST-124",
                        "fields": {
                            "summary": "Blocked Issue"
                        }
                    }
                },
                {
                    "type": {
                        "name": "Relates",
                        "inward": "relates to",
                        "outward": "relates to"
                    },
                    "inwardIssue": {
                        "key": "TEST-125",
                        "fields": {
                            "summary": "Related Issue"
                        }
                    }
                }
            ]
        }
    }


@pytest.fixture
def projects_response():
    """Fixture for JIRA projects response."""
    return [
        {
            "key": "TEST",
            "name": "Test Project",
            "id": "10000"
        },
        {
            "key": "DEMO",
            "name": "Demo Project",
            "id": "10001"
        }
    ]


@pytest.fixture
def transitions_response():
    """Fixture for JIRA transitions response."""
    return {
        "transitions": [
            {
                "id": "11",
                "name": "To Do"
            },
            {
                "id": "21",
                "name": "In Progress"
            },
            {
                "id": "31",
                "name": "Done"
            }
        ]
    }


@pytest.fixture
def create_issue_response():
    """Fixture for JIRA create issue response."""
    return {
        "key": "TEST-123"
    } 