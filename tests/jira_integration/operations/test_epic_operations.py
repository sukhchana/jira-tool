import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from http import HTTPStatus
import os
import time

from jira_integration.operations.epic_operations import EpicOperations
from models.jira_ticket_creation import JiraTicketCreation
from models.jira_epic_details import JiraEpicDetails
from models.jira_epic_progress import JiraEpicProgress


class TestEpicOperations:
    """Test suite for the EpicOperations class."""
    
    # Class variables to store keys between tests
    _integration_epic_key = None
    _integration_story_key = None

    @pytest.fixture
    def run_integration_tests(self):
        """Check if integration tests should be run."""
        return os.environ.get("RUN_JIRA_INTEGRATION_TESTS", "false").lower() == "true"
    
    @pytest.fixture
    def test_project_key(self):
        """Get the test project key from environment variables."""
        return os.environ.get("JIRA_TEST_PROJECT", "DP")
    
    @pytest.fixture
    async def integration_epic_key(self, epic_ops, test_project_key, run_integration_tests):
        """Epic key to use for integration tests.
        
        This fixture searches for existing test epics in the project or creates a new one if needed.
        """
        if not run_integration_tests:
            return "TEST-123"  # Return a dummy value for mock tests
            
        # Use the class variable if it exists (for same test run)
        if TestEpicOperations._integration_epic_key:
            return TestEpicOperations._integration_epic_key
            
        try:
            # Search for existing test epics in the project
            jql = f'project = {test_project_key} AND issuetype = Epic AND summary ~ "Integration Test Epic" ORDER BY created DESC'
            issues = await epic_ops._search_issues(jql)
            
            if issues and len(issues) > 0:
                # Use the most recently created test epic
                epic_key = issues[0]["key"]
                print(f"Using existing test epic: {epic_key}")
                TestEpicOperations._integration_epic_key = epic_key
                return epic_key
                
            # If no existing test epics found, create a new one
            print("No existing test epics found, creating a new one")
            result = await epic_ops.create_epic(
                project_key=test_project_key,
                summary=f"Integration Test Epic {time.time()}",
                description="This is an integration test epic created by automated tests",
                assignee=os.environ.get("JIRA_EMAIL")
            )
            
            TestEpicOperations._integration_epic_key = result.key
            print(f"Created new test epic: {result.key}")
            return result.key
            
        except Exception as e:
            print(f"Error finding/creating test epic: {str(e)}")
            # Fallback to environment variable
            return os.environ.get("JIRA_TEST_EPIC_KEY", "DP-1")

    @pytest.fixture
    def epic_ops(self):
        """Create an EpicOperations instance."""
        return EpicOperations()
        
    @pytest.fixture
    async def integration_story_key(self, run_integration_tests, integration_epic_key, test_project_key):
        """Story key to use for integration tests.
        
        This fixture searches for existing test stories or creates a new one if needed.
        """
        if not run_integration_tests:
            return "TEST-456"  # Return a dummy value for mock tests
            
        # Use the class variable if it exists (for same test run)
        if TestEpicOperations._integration_story_key:
            return TestEpicOperations._integration_story_key
            
        # Create a new story for testing if we don't have one
        try:
            from jira_integration.operations.ticket_operations import TicketOperations
            ticket_ops = TicketOperations()
            
            # First check if there are existing test stories
            jql = f'project = {test_project_key} AND issuetype = Story AND summary ~ "Test Story for Epic Assignment" ORDER BY created DESC'
            issues = await ticket_ops._search_issues(jql)
            
            if issues and len(issues) > 0:
                # Use the most recently created test story
                story_key = issues[0]["key"]
                print(f"Using existing test story: {story_key}")
                TestEpicOperations._integration_story_key = story_key
                return story_key
            
            # Create a new story
            story = await ticket_ops.create_story(
                project_key=test_project_key,
                summary=f"Test Story for Epic Assignment {time.time()}",
                description="This is a test story created for epic assignment testing",
                assignee=os.environ.get("JIRA_EMAIL")
            )
            
            TestEpicOperations._integration_story_key = story.key
            print(f"Created new test story: {story.key}")
            return story.key
            
        except Exception as e:
            print(f"Error finding/creating test story: {str(e)}")
            return None

    @pytest.mark.asyncio
    async def test_create_epic(self, epic_ops, run_integration_tests, test_project_key, mock_aiohttp_session=None, create_issue_response=None, mock_response=None):
        """Test creating an epic."""
        if run_integration_tests:
            # Integration test - create a real epic
            result = await epic_ops.create_epic(
                project_key=test_project_key,
                summary=f"Integration Test Epic {time.time()}",
                description="This is an integration test epic created by automated tests",
                assignee=os.environ.get("JIRA_EMAIL")
            )
            
            # Assert
            assert isinstance(result, JiraTicketCreation)
            assert result.key.startswith(test_project_key)
            assert result.issue_type == "Epic"
            
            # Store the epic key for other tests to use
            TestEpicOperations._integration_epic_key = result.key
            print(f"Created integration test epic: {result.key}")
            
        else:
            # Mock test - use mocks
            # Arrange
            mock_resp = mock_response(status=HTTPStatus.CREATED, json_data=create_issue_response)
            mock_aiohttp_session.post.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))

            # Act
            result = await epic_ops.create_epic(
                project_key="TEST",
                summary="Test Epic",
                description="This is a test epic",
                assignee="user@example.com"
            )

            # Assert
            assert isinstance(result, JiraTicketCreation)
            assert result.key == "TEST-123"
            
            # Verify the request was made with correct data
            mock_aiohttp_session.post.assert_called_once()
            call_args = mock_aiohttp_session.post.call_args[0][1]
            assert "TEST" in str(call_args)
            assert "Epic" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_epic_details(self, epic_ops, run_integration_tests, integration_epic_key, mock_aiohttp_session=None, epic_issue_response=None, epic_linked_issues_response=None, mock_response=None):
        """Test getting epic details."""
        if run_integration_tests:
            # Skip if we don't have a valid epic key
            if not integration_epic_key or integration_epic_key == "DP-1":
                pytest.skip("No valid epic key available for integration test")
                
            # Integration test - get details of a real epic
            result = await epic_ops.get_epic_details(integration_epic_key)
            
            # Assert
            assert isinstance(result, JiraEpicDetails)
            assert result.key == integration_epic_key
            assert result.summary is not None
            assert result.status is not None
            
        else:
            # Mock test - use mocks
            # Arrange - First for epic details, then for linked issues
            mock_epic_response = mock_response(status=HTTPStatus.OK, json_data=epic_issue_response)
            mock_links_response = mock_response(status=HTTPStatus.OK, json_data=epic_linked_issues_response)
            
            # Setup for two different responses
            mock_aiohttp_session.get.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_epic_response)),
                AsyncMock(__aenter__=AsyncMock(return_value=mock_links_response))
            ]

            # Act
            result = await epic_ops.get_epic_details("TEST-E123")

            # Assert
            assert isinstance(result, JiraEpicDetails)
            assert result.key == "TEST-E123"
            assert result.summary == "Test Issue"
            assert result.status == "To Do"
            assert len(result.stories) + len(result.tasks) + len(result.subtasks) == 2
            
            # Verify the calls were made correctly
            assert mock_aiohttp_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_epic_progress(self, epic_ops, run_integration_tests, integration_epic_key, mock_aiohttp_session=None, epic_linked_issues_response=None, mock_response=None):
        """Test getting epic progress."""
        if run_integration_tests:
            # Skip if we don't have a valid epic key
            if not integration_epic_key or integration_epic_key == "DP-1":
                pytest.skip("No valid epic key available for integration test")
                
            # Integration test - get progress of a real epic
            result = await epic_ops.get_epic_progress(integration_epic_key)
            
            # Assert
            assert isinstance(result, JiraEpicProgress)
            assert result.total_issues >= 0
            assert result.completion_percentage >= 0
            
        else:
            # Mock test - use mocks
            # Arrange
            mock_resp = mock_response(status=HTTPStatus.OK, json_data=epic_linked_issues_response)
            mock_aiohttp_session.get.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))

            # Act
            result = await epic_ops.get_epic_progress("TEST-E123")

            # Assert
            assert isinstance(result, JiraEpicProgress)
            assert result.total_issues == 2
            assert result.completed_issues == 1  # One issue has status "Done"
            assert result.completion_percentage == 50.0  # 1 out of 2 issues are Done
            
            # Verify the request was made correctly
            mock_aiohttp_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_epic_details(self, epic_ops, run_integration_tests, integration_epic_key, mock_aiohttp_session=None, mock_response=None):
        """Test updating epic details."""
        if run_integration_tests:
            # Skip if we don't have a valid epic key
            if not integration_epic_key or integration_epic_key == "DP-1":
                pytest.skip("No valid epic key available for integration test")
                
            # Integration test - update a real epic
            timestamp = int(time.time())
            result = await epic_ops.update_epic_details(
                epic_key=integration_epic_key,
                summary=f"Updated Epic {timestamp}",
                description=f"Updated Description {timestamp}"
            )
            
            # Assert
            assert result is True
            
            # Verify the update was successful by getting the epic details
            updated_epic = await epic_ops.get_epic_details(integration_epic_key)
            assert f"Updated Epic {timestamp}" in updated_epic.summary
            assert f"Updated Description {timestamp}" in updated_epic.description
            
        else:
            # Mock test - use mocks
            # Arrange
            mock_resp = mock_response(status=HTTPStatus.NO_CONTENT)
            mock_aiohttp_session.put.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))

            # Act
            result = await epic_ops.update_epic_details(
                epic_key="TEST-123", summary="Updated Epic", description="Updated Description"
            )

            # Assert
            assert result is True
            
            # Verify the request was made correctly
            mock_aiohttp_session.put.assert_called_once()
            call_args = mock_aiohttp_session.put.call_args[0][1]
            assert "TEST-123" in str(call_args)
            assert "Updated Epic" in str(call_args)
            assert "Updated Description" in str(call_args)

    @pytest.mark.asyncio
    async def test_assign_issue_to_epic(self, epic_ops, run_integration_tests, integration_epic_key, integration_story_key, test_project_key, mock_aiohttp_session=None, mock_response=None):
        """Test assigning an issue to an epic."""
        if run_integration_tests:
            # Skip if we don't have a valid epic key
            if not integration_epic_key or integration_epic_key == "DP-1":
                pytest.skip("No valid epic key available for integration test")
                
            # Skip if we don't have a valid story key
            if not integration_story_key:
                pytest.skip("No valid story key available for integration test")
            
            # Log the keys we're using for debugging
            print(f"Using epic key: {integration_epic_key}")
            print(f"Using story key: {integration_story_key}")
                
            # Now assign the story to the epic
            result = await epic_ops.assign_issue_to_epic(integration_epic_key, integration_story_key)
            
            # Assert
            assert result is True, f"Failed to assign story {integration_story_key} to epic {integration_epic_key}"
            
        else:
            # Mock test - use mocks
            # Arrange
            mock_resp = mock_response(status=HTTPStatus.NO_CONTENT)
            mock_aiohttp_session.put.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))

            # Act
            result = await epic_ops.assign_issue_to_epic("TEST-E123", "TEST-456")

            # Assert
            assert result is True
            
            # Verify the request was made correctly
            mock_aiohttp_session.put.assert_called_once()
            call_args = mock_aiohttp_session.put.call_args[0][1]
            assert "TEST-456" in str(call_args)
            assert "epic" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_remove_issue_from_epic(self, epic_ops, run_integration_tests, integration_story_key, mock_aiohttp_session=None, mock_response=None):
        """Test removing an issue from an epic."""
        if run_integration_tests:
            # Skip if we don't have a valid story key
            if not integration_story_key:
                pytest.skip("No story key available for integration test")
                
            # Log the key we're using for debugging
            print(f"Using story key for removal: {integration_story_key}")
            
            # Remove the story from the epic
            result = await epic_ops.remove_issue_from_epic(integration_story_key)
            
            # Assert
            assert result is True, f"Failed to remove story {integration_story_key} from its epic"
            
        else:
            # Mock test - use mocks
            # Arrange
            mock_resp = mock_response(status=HTTPStatus.NO_CONTENT)
            mock_aiohttp_session.put.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))

            # Act
            result = await epic_ops.remove_issue_from_epic("TEST-456")

            # Assert
            assert result is True
            
            # Verify the request was made correctly
            mock_aiohttp_session.put.assert_called_once()
            call_args = mock_aiohttp_session.put.call_args[0][1]
            assert "TEST-456" in str(call_args)
            assert "null" in str(call_args).lower()  # Removing means setting epic link to null 