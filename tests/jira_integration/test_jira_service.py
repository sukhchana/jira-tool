import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from jira_integration.jira_service import JiraService
from jira_integration.operations.ticket_operations import TicketOperations
from jira_integration.operations.epic_operations import EpicOperations
from jira_integration.models import (
    JiraTicketCreation, 
    JiraTicketDetails,
    JiraLinkedTicket,
    JiraEpicDetails,
    JiraEpicProgress
)


class TestJiraService:
    """Test suite for the JiraService class."""

    @pytest.fixture
    def mock_ticket_ops(self):
        """Mock the TicketOperations class."""
        mock = AsyncMock(spec=TicketOperations)
        mock.create_story.return_value = JiraTicketCreation(
            key="TEST-123",
            summary="Test Story"
        )
        mock.create_task.return_value = JiraTicketCreation(
            key="TEST-124",
            summary="Test Task"
        )
        mock.create_subtask.return_value = JiraTicketCreation(
            key="TEST-125",
            summary="Test Subtask"
        )
        
        mock.get_ticket_details.return_value = JiraTicketDetails(
            key="TEST-123", 
            summary="Test Issue", 
            description="Description", 
            status="To Do", 
            assignee="Test User", 
            issue_type="Story", 
            created="2023-01-01T12:00:00.000+0000", 
            updated="2023-01-02T12:00:00.000+0000",
            project_key="TEST"
        )
        
        mock.get_linked_tickets.return_value = [
            JiraLinkedTicket(key="TEST-124", summary="Linked Issue", relationship="blocks"),
            JiraLinkedTicket(key="TEST-125", summary="Related Issue", relationship="relates to")
        ]
        
        mock.update_ticket_status.return_value = True
        mock.add_comment.return_value = True
        
        return mock

    @pytest.fixture
    def mock_epic_ops(self):
        """Mock the EpicOperations class."""
        mock = AsyncMock(spec=EpicOperations)
        mock.create_epic.return_value = JiraTicketCreation(
            key="TEST-E123",
            summary="Test Epic"
        )
        
        mock.get_epic_details.return_value = JiraEpicDetails(
            key="TEST-E123", 
            summary="Test Epic", 
            description="Description", 
            status="To Do",
            project_key="TEST",
            assignee="Test User", 
            created="2023-01-01T12:00:00.000+0000", 
            updated="2023-01-02T12:00:00.000+0000",
            linked_issues=[
                JiraTicketDetails(
                    key="TEST-124", 
                    summary="Linked Story", 
                    description="Description", 
                    status="In Progress", 
                    assignee=None, 
                    issue_type="Story", 
                    created="2023-01-01T12:00:00.000+0000", 
                    updated="2023-01-02T12:00:00.000+0000",
                    project_key="TEST"
                ),
                JiraTicketDetails(
                    key="TEST-125", 
                    summary="Linked Task", 
                    description="Description", 
                    status="Done", 
                    assignee=None, 
                    issue_type="Task", 
                    created="2023-01-01T12:00:00.000+0000", 
                    updated="2023-01-02T12:00:00.000+0000",
                    project_key="TEST"
                )
            ]
        )
        
        mock.get_epic_progress.return_value = JiraEpicProgress(
            total_issues=2,
            completed_issues=1,
            completion_percentage=50.0,
            stories_count=1,
            tasks_count=1,
            subtasks_count=0,
            done_issues=1
        )
        
        mock.assign_issue_to_epic.return_value = True
        mock.remove_issue_from_epic.return_value = True
        mock.update_epic_details.return_value = True
        
        return mock

    @pytest.fixture
    def jira_service(self, mock_ticket_ops, mock_epic_ops):
        """Create a JiraService instance with mocked operations."""
        with patch('jira_integration.jira_service.TicketOperations', return_value=mock_ticket_ops), \
             patch('jira_integration.jira_service.EpicOperations', return_value=mock_epic_ops):
            return JiraService()

    @pytest.mark.asyncio
    async def test_get_ticket(self, jira_service, mock_ticket_ops):
        """Test getting a ticket."""
        # Act
        result = await jira_service.get_ticket("TEST-123")
        
        # Assert
        assert isinstance(result, JiraTicketDetails)
        assert result.key == "TEST-123"
        mock_ticket_ops.get_ticket_details.assert_called_once_with("TEST-123")

    @pytest.mark.asyncio
    async def test_create_story(self, jira_service, mock_ticket_ops):
        """Test creating a story."""
        # Act
        result = await jira_service.create_story(
            project_key="TEST", 
            summary="New Story", 
            description="Description", 
            assignee="user@example.com"
        )
        
        # Assert
        assert isinstance(result, JiraTicketCreation)
        assert result.key == "TEST-123"
        mock_ticket_ops.create_story.assert_called_once_with(
            project_key="TEST",
            summary="New Story",
            description="Description",
            additional_fields={'assignee': {'name': 'user@example.com'}}
        )

    @pytest.mark.asyncio
    async def test_create_task(self, jira_service, mock_ticket_ops):
        """Test creating a task."""
        # Act
        result = await jira_service.create_task(
            project_key="TEST", 
            summary="New Task", 
            description="Description", 
            assignee="user@example.com"
        )
        
        # Assert
        assert isinstance(result, JiraTicketCreation)
        assert result.key == "TEST-124"
        mock_ticket_ops.create_task.assert_called_once_with(
            project_key="TEST",
            summary="New Task",
            description="Description",
            additional_fields={'assignee': {'name': 'user@example.com'}}
        )

    @pytest.mark.asyncio
    async def test_create_subtask(self, jira_service, mock_ticket_ops):
        """Test creating a subtask."""
        # Act
        result = await jira_service.create_subtask(
            parent_key="TEST-123",
            project_key="TEST", 
            summary="New Subtask", 
            description="Description", 
            assignee="user@example.com"
        )
        
        # Assert
        assert isinstance(result, JiraTicketCreation)
        assert result.key == "TEST-125"
        mock_ticket_ops.create_subtask.assert_called_once_with(
            parent_key="TEST-123",
            project_key="TEST",
            summary="New Subtask",
            description="Description",
            additional_fields={'assignee': {'name': 'user@example.com'}}
        )

    @pytest.mark.asyncio
    async def test_update_ticket_status(self, jira_service, mock_ticket_ops):
        """Test updating a ticket status."""
        # Act
        result = await jira_service.update_ticket_status("TEST-123", "In Progress")
        
        # Assert
        assert result is True
        mock_ticket_ops.update_ticket_status.assert_called_once_with("TEST-123", "In Progress")

    @pytest.mark.asyncio
    async def test_add_comment(self, jira_service, mock_ticket_ops):
        """Test adding a comment to a ticket."""
        # Act
        result = await jira_service.add_comment("TEST-123", "Test comment")
        
        # Assert
        assert result is True
        mock_ticket_ops.add_comment.assert_called_once_with("TEST-123", "Test comment")

    @pytest.mark.asyncio
    async def test_get_linked_tickets(self, jira_service, mock_ticket_ops):
        """Test getting linked tickets."""
        # Act
        result = await jira_service.get_linked_tickets("TEST-123")
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(ticket, JiraLinkedTicket) for ticket in result)
        mock_ticket_ops.get_linked_tickets.assert_called_once_with("TEST-123")

    @pytest.mark.asyncio
    async def test_create_epic(self, jira_service, mock_epic_ops):
        """Test creating an epic."""
        # Act
        result = await jira_service.create_epic(
            project_key="TEST", 
            summary="New Epic", 
            description="Description", 
            assignee="user@example.com"
        )
        
        # Assert
        assert isinstance(result, JiraTicketCreation)
        assert result.key == "TEST-E123"
        mock_epic_ops.create_epic.assert_called_once_with(
            project_key="TEST",
            summary="New Epic",
            description="Description",
            additional_fields={'assignee': {'name': 'user@example.com'}}
        )

    @pytest.mark.asyncio
    async def test_get_epic_details(self, jira_service, mock_epic_ops):
        """Test getting epic details."""
        # Act
        result = await jira_service.get_epic_details("TEST-E123")
        
        # Assert
        assert isinstance(result, JiraEpicDetails)
        assert result.key == "TEST-E123"
        assert len(result.linked_issues) == 2
        mock_epic_ops.get_epic_details.assert_called_once_with("TEST-E123")

    @pytest.mark.asyncio
    async def test_get_epic_progress(self, jira_service, mock_epic_ops):
        """Test getting epic progress."""
        # Act
        result = await jira_service.get_epic_progress("TEST-E123")
        
        # Assert
        assert isinstance(result, JiraEpicProgress)
        assert result.total_issues == 2
        assert result.done_issues == 1
        assert result.completion_percentage == 50.0
        mock_epic_ops.get_epic_progress.assert_called_once_with("TEST-E123")

    @pytest.mark.asyncio
    async def test_assign_to_epic(self, jira_service, mock_epic_ops):
        """Test assigning an issue to an epic."""
        # Act
        result = await jira_service.assign_to_epic("TEST-E123", "TEST-456")
        
        # Assert
        assert result is True
        mock_epic_ops.assign_issue_to_epic.assert_called_once_with("TEST-E123", "TEST-456")

    @pytest.mark.asyncio
    async def test_remove_from_epic(self, jira_service, mock_epic_ops):
        """Test removing an issue from an epic."""
        # Act
        result = await jira_service.remove_from_epic("TEST-456")
        
        # Assert
        assert result is True
        mock_epic_ops.remove_issue_from_epic.assert_called_once_with("TEST-456")

    @pytest.mark.asyncio
    async def test_update_epic(self, jira_service, mock_epic_ops):
        """Test updating epic details."""
        # Act
        update_data = {"summary": "Updated Epic", "description": "Updated description"}
        result = await jira_service.update_epic("TEST-E123", update_data)
        
        # Assert
        assert result is True
        mock_epic_ops.update_epic_details.assert_called_once_with(
            epic_key="TEST-E123",
            summary="Updated Epic",
            description="Updated description"
        ) 