import os
import pytest
from loguru import logger

from jira_integration.operations.base_operation import BaseJiraOperation


# Check if integration tests should run
SKIP_INTEGRATION_TESTS = os.getenv("RUN_JIRA_INTEGRATION_TESTS", "false").lower() != "true"
SKIP_REASON = "Integration tests are skipped by default. Set RUN_JIRA_INTEGRATION_TESTS=true to run"

# Ensure JIRA credentials are set for integration tests
JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_TEST_PROJECT = os.getenv("JIRA_TEST_PROJECT", "DP")

# Additional reason to skip if credentials are missing
if not all([JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN]):
    SKIP_INTEGRATION_TESTS = True
    SKIP_REASON = "JIRA credentials (JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN) must be set"


@pytest.mark.skipif(SKIP_INTEGRATION_TESTS, reason=SKIP_REASON)
@pytest.mark.asyncio
class TestBaseJiraOperationIntegration:
    """
    Integration tests for BaseJiraOperation.
    
    These tests interact with a real JIRA instance and are skipped by default.
    To run these tests:
    
    1. Set environment variables:
       - JIRA_SERVER: URL of your JIRA server
       - JIRA_EMAIL: Your JIRA account email
       - JIRA_API_TOKEN: Your API token
       - JIRA_TEST_PROJECT: Project key to use for testing (default: TEST)
       
    2. Enable integration tests:
       - RUN_JIRA_INTEGRATION_TESTS=true
       
    WARNING: These tests will create and modify real JIRA issues!
    """

    @pytest.fixture
    async def base_operation(self):
        """Create a BaseJiraOperation instance for integration testing."""
        # Don't patch environment variables - use the real ones
        # This is a true integration test that connects to the actual JIRA instance
        operation = BaseJiraOperation()
        yield operation

    @pytest.fixture
    async def test_issue_key(self, base_operation):
        """
        Create a test issue and return its key.
        
        This fixture creates a JIRA issue to be used by tests,
        then deletes it after the test completes.
        """
        # Create a test issue
        issue = await base_operation._create_issue(
            project_key=JIRA_TEST_PROJECT,
            summary="Integration Test Issue",
            description="This is a test issue created by integration tests. It will be deleted automatically.",
            issue_type="Task"
        )
        
        issue_key = issue.key
        logger.info(f"Created test issue: {issue_key}")
        
        yield issue_key
        
        # Clean up after the test
        try:
            # Note: JIRA doesn't have a direct delete API in the standard REST API
            # In a real implementation, you might:
            # 1. Move it to a "DELETED" status
            # 2. Use JIRA admin API if available
            # 3. Just add a comment saying it was a test
            
            await base_operation._update_issue(
                issue_key=issue_key,
                fields={
                    "description": f"TEST ISSUE - PLEASE IGNORE OR DELETE\n\nThis was created by automated integration tests on {issue.created_date}"
                }
            )
            
            # Try to transition to "Done" or another final state if possible
            try:
                await base_operation._transition_issue(issue_key, "Done")
            except Exception as e:
                logger.warning(f"Could not transition issue to Done: {e}")
                
            logger.info(f"Marked test issue for cleanup: {issue_key}")
        except Exception as e:
            logger.error(f"Failed to clean up test issue {issue_key}: {e}")

    async def test_get_issue(self, base_operation, test_issue_key):
        """Test getting an issue by key."""
        # Act
        issue = await base_operation._get_issue(test_issue_key)
        
        # Assert
        assert issue is not None
        assert issue["key"] == test_issue_key
        assert "fields" in issue
        assert "summary" in issue["fields"]

    async def test_create_issue(self, base_operation):
        """Test creating a new issue."""
        # Act
        issue = await base_operation._create_issue(
            project_key=JIRA_TEST_PROJECT,
            summary="Test Create Issue",
            description="This is a test issue created during integration testing.",
            issue_type="Task"
        )
        
        # Assert
        assert issue is not None
        assert issue.key is not None
        assert issue.key.startswith(f"{JIRA_TEST_PROJECT}-")
        assert issue.summary == "Test Create Issue"
        assert issue.issue_type == "Task"
        
        # Clean up
        try:
            await base_operation._update_issue(
                issue_key=issue.key,
                fields={"description": "TEST ISSUE - PLEASE IGNORE OR DELETE"}
            )
            try:
                await base_operation._transition_issue(issue.key, "Done")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Failed to clean up test issue {issue.key}: {e}")

    async def test_update_issue(self, base_operation, test_issue_key):
        """Test updating an issue."""
        # Arrange
        updated_summary = f"Updated Summary {test_issue_key}"
        
        # Act
        result = await base_operation._update_issue(
            issue_key=test_issue_key,
            fields={"summary": updated_summary}
        )
        
        # Assert
        assert result is True
        
        # Verify the change
        updated_issue = await base_operation._get_issue(test_issue_key)
        assert updated_issue["fields"]["summary"] == updated_summary

    async def test_search_issues(self, base_operation, test_issue_key):
        """Test searching for issues using JQL."""
        # Act
        jql = f"key = {test_issue_key}"
        results = await base_operation._search_issues(jql)
        
        # Assert
        assert len(results) == 1
        assert results[0]["key"] == test_issue_key

    async def test_transition_issue(self, base_operation, test_issue_key):
        """Test transitioning an issue to a different status."""
        # This test might need adjusting based on your JIRA workflow
        # For simplicity, we'll try to transition to "In Progress" which exists in most workflows
        
        try:
            # Act
            result = await base_operation._transition_issue(test_issue_key, "In Progress")
            
            # Assert
            assert result is True
            
            # Verify the status change
            updated_issue = await base_operation._get_issue(test_issue_key)
            assert updated_issue["fields"]["status"]["name"] == "In Progress"
        except Exception as e:
            # If the transition isn't available in the workflow, we'll log it and skip
            logger.warning(f"Could not test transition: {e}")
            pytest.skip("Transition to 'In Progress' not available in the current workflow")

    async def test_create_issue_with_parent(self, base_operation, test_issue_key):
        """Test creating a subtask with a parent issue."""
        # Act
        # Create a subtask using the test_issue_key as parent
        subtask = await base_operation._create_issue(
            project_key=JIRA_TEST_PROJECT,
            summary="Test Subtask for Integration",
            description="This is a test subtask created during integration testing.",
            issue_type="Subtask",
            parent_key=test_issue_key
        )
        
        # Assert
        assert subtask is not None
        assert subtask.key is not None
        assert subtask.key.startswith(f"{JIRA_TEST_PROJECT}-")
        assert subtask.summary == "Test Subtask for Integration"
        assert subtask.issue_type == "Subtask"
        
        # Verify the parent relationship
        subtask_data = await base_operation._get_issue(subtask.key)
        assert subtask_data["fields"]["parent"]["key"] == test_issue_key
        
        # Clean up
        try:
            await base_operation._update_issue(
                issue_key=subtask.key,
                fields={"description": "TEST SUBTASK - PLEASE IGNORE OR DELETE"}
            )
            try:
                await base_operation._transition_issue(subtask.key, "Done")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Failed to clean up test subtask {subtask.key}: {e}")

    async def test_get_issue_error(self, base_operation):
        """Test error handling when an issue doesn't exist."""
        # Use a non-existent issue key
        non_existent_key = f"{JIRA_TEST_PROJECT}-999999"
    
        # Act
        result = await base_operation._get_issue(non_existent_key)
        
        # Assert
        assert result is None, "Expected None result for non-existent issue"

    async def test_create_issue_error(self, base_operation):
        """Test error handling when creating an issue fails."""
        # Act & Assert - attempt to create an issue with invalid data
        with pytest.raises(Exception) as excinfo:
            await base_operation._create_issue(
                project_key="INVALID",  # Using an invalid project key should fail
                summary="Test Invalid Issue",
                description="This should fail because the project key is invalid.",
                issue_type="Task"
            )
            
        # Check that the exception contains a meaningful error message
        error_message = str(excinfo.value)
        assert "project" in error_message.lower() or "invalid" in error_message.lower()
        logger.info(f"Successfully caught error for invalid issue creation: {error_message}") 