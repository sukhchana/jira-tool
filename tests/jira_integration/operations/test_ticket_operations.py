import pytest
import os
import time
from unittest.mock import AsyncMock, patch, MagicMock
from http import HTTPStatus

from jira_integration.operations.ticket_operations import TicketOperations
from models.jira_ticket_creation import JiraTicketCreation
from models.jira_ticket_details import JiraTicketDetails
from models.jira_linked_ticket import JiraLinkedTicket


class TestTicketOperations:
    """Test suite for the TicketOperations class."""
    
    # Class variables to store keys between tests
    _integration_ticket_key = None

    @pytest.fixture
    def run_integration_tests(self):
        """Check if integration tests should be run."""
        return os.environ.get("RUN_JIRA_INTEGRATION_TESTS", "false").lower() == "true"
    
    @pytest.fixture
    def test_project_key(self):
        """Get the test project key from environment variables."""
        return os.environ.get("JIRA_TEST_PROJECT", "DP")
    
    @pytest.fixture
    def integration_ticket_key(self):
        """Ticket key to use for integration tests."""
        # Use the class variable if it exists
        if TestTicketOperations._integration_ticket_key:
            return TestTicketOperations._integration_ticket_key
        # Fallback to environment variable
        return os.environ.get("JIRA_TEST_TICKET_KEY", "")

    @pytest.fixture
    def ticket_ops(self):
        """Create a TicketOperations instance."""
        return TicketOperations()

    @pytest.mark.asyncio
    async def test_create_story(self, ticket_ops, run_integration_tests, test_project_key):
        """Test creating a story ticket."""
        if not run_integration_tests:
            pytest.skip("Skipping integration test - RUN_JIRA_INTEGRATION_TESTS not set to true")
            
        # Integration test - create a real story
        result = await ticket_ops.create_story(
            project_key=test_project_key,
            summary=f"Integration Test Story {time.time()}",
            description="This is an integration test story created by automated tests",
            assignee=os.environ.get("JIRA_EMAIL")
        )
        
        # Assert
        assert isinstance(result, JiraTicketCreation)
        assert result.key.startswith(test_project_key)
        assert result.issue_type == "Story"
        
        # Store the ticket key for other tests to use
        TestTicketOperations._integration_ticket_key = result.key
        print(f"Created integration test story: {result.key}")

    @pytest.mark.asyncio
    async def test_create_task(self, ticket_ops, run_integration_tests, test_project_key):
        """Test creating a task ticket."""
        if not run_integration_tests:
            pytest.skip("Skipping integration test - RUN_JIRA_INTEGRATION_TESTS not set to true")
            
        # Integration test - create a real task
        result = await ticket_ops.create_task(
            project_key=test_project_key,
            summary=f"Integration Test Task {time.time()}",
            description="This is an integration test task created by automated tests",
            assignee=os.environ.get("JIRA_EMAIL")
        )
        
        # Assert
        assert isinstance(result, JiraTicketCreation)
        assert result.key.startswith(test_project_key)
        assert result.issue_type == "Task"

    @pytest.mark.asyncio
    async def test_create_subtask(self, ticket_ops, run_integration_tests, test_project_key, integration_ticket_key):
        """Test creating a subtask ticket."""
        if not run_integration_tests:
            pytest.skip("Skipping integration test - RUN_JIRA_INTEGRATION_TESTS not set to true")
            
        # Skip if we don't have a valid parent ticket key
        if not integration_ticket_key:
            pytest.skip("No valid parent ticket key available for integration test")
            
        # Integration test - create a real subtask
        result = await ticket_ops.create_subtask(
            parent_key=integration_ticket_key,
            project_key=test_project_key,
            summary=f"Integration Test Subtask {time.time()}",
            description="This is an integration test subtask created by automated tests",
            assignee=os.environ.get("JIRA_EMAIL")
        )
        
        # Assert
        assert isinstance(result, JiraTicketCreation)
        assert result.key.startswith(test_project_key)
        assert result.issue_type == "Subtask"

    @pytest.mark.asyncio
    async def test_get_ticket_details(self, ticket_ops, run_integration_tests, integration_ticket_key):
        """Test getting ticket details."""
        if not run_integration_tests:
            pytest.skip("Skipping integration test - RUN_JIRA_INTEGRATION_TESTS not set to true")
            
        # Skip if we don't have a valid ticket key
        if not integration_ticket_key:
            pytest.skip("No valid ticket key available for integration test")
            
        # Integration test - get details of a real ticket
        result = await ticket_ops.get_ticket_details(integration_ticket_key)
        
        # Assert
        assert isinstance(result, JiraTicketDetails)
        assert result.key == integration_ticket_key
        assert result.summary is not None
        assert result.status is not None

    @pytest.mark.asyncio
    async def test_get_linked_tickets(self, ticket_ops, run_integration_tests, integration_ticket_key):
        """Test getting linked tickets."""
        if not run_integration_tests:
            pytest.skip("Skipping integration test - RUN_JIRA_INTEGRATION_TESTS not set to true")
            
        # Skip if we don't have a valid ticket key
        if not integration_ticket_key:
            pytest.skip("No valid ticket key available for integration test")
            
        # Integration test - get linked tickets of a real ticket
        result = await ticket_ops.get_linked_tickets(integration_ticket_key)
        
        # Assert - just check the type, as there might not be any linked tickets
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_ticket_status(self, ticket_ops, run_integration_tests, integration_ticket_key):
        """Test updating ticket status."""
        if not run_integration_tests:
            pytest.skip("Skipping integration test - RUN_JIRA_INTEGRATION_TESTS not set to true")
            
        # Skip if we don't have a valid ticket key
        if not integration_ticket_key:
            pytest.skip("No valid ticket key available for integration test")
            
        # Integration test - update status of a real ticket
        # First get the current status
        ticket_details = await ticket_ops.get_ticket_details(integration_ticket_key)
        current_status = ticket_details.status
        
        # Determine a new status to transition to
        # This is simplified and might need adjustment based on your workflow
        new_status = "In Progress" if current_status != "In Progress" else "To Do"
        
        # Update the status
        result = await ticket_ops.update_ticket_status(integration_ticket_key, new_status)
        
        # Assert
        assert result is True
        
        # Verify the status was updated
        updated_ticket = await ticket_ops.get_ticket_details(integration_ticket_key)
        assert updated_ticket.status == new_status

    @pytest.mark.asyncio
    async def test_add_comment(self, ticket_ops, run_integration_tests, integration_ticket_key):
        """Test adding a comment to a ticket."""
        if not run_integration_tests:
            pytest.skip("Skipping integration test - RUN_JIRA_INTEGRATION_TESTS not set to true")
            
        # Skip if we don't have a valid ticket key
        if not integration_ticket_key:
            pytest.skip("No valid ticket key available for integration test")
            
        # Integration test - add comment to a real ticket
        comment_text = f"Integration test comment {time.time()}"
        result = await ticket_ops.add_comment(integration_ticket_key, comment_text)
        
        # Assert
        assert result is True 