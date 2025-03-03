import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import json

from models.analysis_info import AnalysisInfo
from models.jira_ticket_details import JiraTicketDetails
from models.user_story import UserStory
from models.technical_task import TechnicalTask
from models.sub_task import SubTask
from models.epic_breakdown_response import EpicBreakdownResponse
from models.story_description import StoryDescription
from models.implementation_notes import ImplementationNotes
from breakdown.execution_manager import ExecutionManager


@pytest.fixture
def epic_key():
    return "TEST-123"


@pytest.fixture
def execution_manager(epic_key):
    manager = ExecutionManager(epic_key)
    
    # Mock services
    manager.jira_service = Mock()
    manager.epic_analyzer = Mock()
    manager.user_story_generator = Mock()
    manager.technical_task_generator = Mock()
    manager.subtask_generator = Mock()
    manager.execution_log = Mock()
    manager.proposed_tickets = Mock()
    
    return manager


@pytest.fixture
def mock_execution_log():
    return Mock()

@pytest.fixture
def mock_jira():
    return Mock()

@pytest.fixture
def mock_task_tracker():
    return Mock()

@pytest.fixture
def mock_proposed_tickets():
    return Mock()


@pytest.mark.asyncio
async def test_analyze_epic_details_success(execution_manager, epic_key):
    # Arrange
    mock_epic_details = JiraTicketDetails(
        key=epic_key,
        summary="Test Epic",
        description="Test Description",
        issue_type="Epic",
        status="Open",
        project_key="TEST",
        created="2024-01-01T00:00:00.000Z",
        updated="2024-01-01T00:00:00.000Z",
        assignee="Test Assignee",
        reporter="Test Reporter",
        priority="High",
        labels=["test"],
        components=["test-component"]
    )
    mock_analysis = AnalysisInfo(
        main_objective="Test Objective",
        technical_domains=["Domain 1"],
        core_requirements=["Req 1"],
        stakeholders=["Stakeholder 1"],
        constraints=["Constraint 1"],
        dependencies=["Dependency 1"]
    )
    
    execution_manager.jira.get_ticket = AsyncMock(
        return_value=mock_epic_details
    )
    execution_manager.epic_analyzer.analyze_epic = AsyncMock(
        return_value=mock_analysis
    )
    execution_manager._save_state = Mock()

    # Act
    epic_details, analysis = await execution_manager.analyze_epic_details()

    # Assert
    assert epic_details == mock_epic_details
    assert analysis == mock_analysis
    execution_manager._save_state.assert_called()
    execution_manager.jira.get_ticket.assert_called_once_with(epic_key)
    execution_manager.epic_analyzer.analyze_epic.assert_called_once_with(
        mock_epic_details.summary,
        mock_epic_details.description
    )


@pytest.mark.asyncio
async def test_generate_user_stories_success(execution_manager):
    # Arrange
    mock_epic_analysis = AnalysisInfo(
        main_objective="Test Objective",
        technical_domains=["Domain 1"],
        core_requirements=["Req 1"],
        stakeholders=["Stakeholder 1"]
    )
    mock_task_tracker = Mock()
    mock_stories = [
        UserStory(
            id="US-1",
            title="Test Story",
            type="User Story",
            description=StoryDescription(
                role="developer",
                goal="implement feature",
                benefit="improve system",
                formatted="As a developer, I want to implement feature, so that I can improve system"
            ),
            technical_domain="Domain 1",
            complexity="Medium",
            business_value="High",
            story_points=3,
            required_skills=["Skill1"],
            suggested_assignee="Test Assignee",
            dependencies=[],
            acceptance_criteria=["Criteria1"],
            implementation_notes=ImplementationNotes()
        )
    ]
    
    execution_manager.user_story_generator.generate_user_stories = AsyncMock(
        return_value=mock_stories
    )
    execution_manager._save_state = Mock()

    # Act
    result = await execution_manager.generate_user_stories(
        mock_epic_analysis,
        mock_task_tracker
    )

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], UserStory)
    assert result[0].id == "US-1"
    assert result[0].title == "Test Story"
    execution_manager._save_state.assert_called()


@pytest.mark.asyncio
async def test_generate_technical_tasks_success(execution_manager):
    # Arrange
    mock_user_stories = [UserStory(
        id="US-1",
        title="Test Story",
        type="User Story",
        description=StoryDescription(
            role="developer",
            goal="implement feature",
            benefit="improve system",
            formatted="As a developer, I want to implement feature, so that I can improve system"
        ),
        technical_domain="Domain 1",
        complexity="Medium",
        business_value="High",
        story_points=3,
        required_skills=["Skill1"],
        suggested_assignee="Test Assignee",
        dependencies=[],
        acceptance_criteria=["Criteria1"],
        implementation_notes=ImplementationNotes()
    )]
    mock_epic_analysis = AnalysisInfo(
        main_objective="Test Objective",
        technical_domains=["Domain 1"],
        core_requirements=["Req 1"],
        stakeholders=["Stakeholder 1"],
        constraints=["Constraint 1"],
        dependencies=["Dependency 1"]
    )
    mock_task_tracker = Mock()
    mock_tasks = [TechnicalTask(
        id="TT-1",
        title="Test Task",
        type="Technical Task",
        description="Test Description",
        technical_domain="Domain 1",
        complexity="Medium",
        business_value="High",
        story_points=3,
        required_skills=["Skill1"],
        suggested_assignee="Test Assignee",
        dependencies=[],
        acceptance_criteria=["Test Criteria"],
        performance_impact="Low impact",
        scalability_considerations="Scales well",
        monitoring_needs="Basic monitoring",
        testing_requirements="Unit tests required",
        implementation_approach={
            "approach": "Test approach",
            "architecture": "Test architecture",
            "data_flow": "Test data flow",
            "security": "Test security",
            "dependencies": "Test dependencies",
            "apis": "Test APIs",
            "database": "Test DB",
            "third_party_services": "None"
        },
        security_considerations="Test security",
        deployment_requirements="Test deployment",
        maintenance_requirements="Test maintenance"
    )]
    
    execution_manager.technical_task_generator.generate_technical_tasks = AsyncMock(
        return_value=mock_tasks
    )
    execution_manager._save_state = Mock()

    # Act
    result = await execution_manager.generate_technical_tasks(
        mock_user_stories,
        mock_epic_analysis,
        mock_task_tracker
    )

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], TechnicalTask)
    assert result[0].id == "TT-1"
    assert result[0].title == "Test Task"
    execution_manager._save_state.assert_called_once_with(
        "technical_tasks.json",
        [task.model_dump() for task in mock_tasks]
    )


@pytest.mark.asyncio
async def test_generate_subtasks_success(execution_manager, epic_key):
    # Arrange
    mock_high_level_tasks = [
        UserStory(
            id="US-1",
            title="Test Story",
            type="User Story",
            description=StoryDescription(
                role="developer",
                goal="implement feature",
                benefit="improve system",
                formatted="As a developer, I want to implement feature, so that I can improve system"
            ),
            technical_domain="Domain 1",
            complexity="Medium",
            business_value="High",
            story_points=3,
            required_skills=["Skill1"],
            suggested_assignee="Test Assignee",
            dependencies=[],
            acceptance_criteria=["Criteria1"],
            implementation_notes=ImplementationNotes()
        )
    ]
    mock_epic_details = JiraTicketDetails(
        key=epic_key,
        summary="Test Epic",
        description="Test Description",
        issue_type="Epic",
        status="Open",
        project_key="TEST",
        created="2024-01-01T00:00:00.000Z",
        updated="2024-01-01T00:00:00.000Z",
        assignee="Test Assignee",
        reporter="Test Reporter",
        priority="High",
        labels=["test"],
        components=["test-component"]
    )
    mock_task_tracker = Mock()
    mock_subtasks = [
        SubTask(
            id="ST-1",
            parent_id="US-1",
            title="Test Subtask",
            type="Sub-task",
            description="Test Description",
            technical_domain="Domain 1",
            complexity="Medium",
            business_value="High",
            story_points=2,
            required_skills=["Skill1"],
            suggested_assignee="Test Assignee",
            dependencies=[],
            acceptance_criteria=["Test Criteria"]
        )
    ]
    
    execution_manager.subtask_generator.break_down_tasks = AsyncMock(
        return_value=mock_subtasks
    )
    execution_manager._save_state = Mock()

    # Act
    result = await execution_manager.generate_subtasks(
        mock_high_level_tasks,
        mock_epic_details,
        mock_task_tracker,
        "user_story"
    )

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], SubTask)
    assert result[0].id == "ST-1"
    assert result[0].title == "Test Subtask"
    execution_manager._save_state.assert_called_once_with(
        "user_story_subtasks.json",
        [subtask.model_dump() for subtask in mock_subtasks]
    )


def test_save_state_success(execution_manager, tmp_path):
    # Arrange
    filename = "test.json"
    data = {"test": "data"}
    execution_manager.state_dir = tmp_path
    
    # Act
    execution_manager._save_state(filename, data)
    
    # Assert
    expected_path = execution_manager.state_dir / filename
    assert expected_path.exists()
    with open(expected_path, 'r') as f:
        saved_data = json.load(f)
        assert saved_data == data


def test_load_state_success(execution_manager, tmp_path):
    # Arrange
    filename = "test.json"
    data = {"test": "data"}
    execution_manager.state_dir = tmp_path
    filepath = execution_manager.state_dir / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f)

    # Act
    result = execution_manager._load_state(filename)

    # Assert
    assert result == data


def test_load_state_file_not_found(execution_manager):
    # Act & Assert
    with pytest.raises(FileNotFoundError):
        execution_manager._load_state("nonexistent.json")


def test_load_execution_state_success(tmp_path):
    # Arrange
    epic_key = "TEST-123"
    execution_id = "test_execution"
    state_file = "test.json"
    data = {"test": "data"}

    # Create execution_states directory
    state_dir = tmp_path / "execution_states" / epic_key / execution_id
    state_dir.mkdir(parents=True, exist_ok=True)
    filepath = state_dir / state_file
    
    # Write test data
    with open(filepath, 'w') as f:
        json.dump(data, f)

    # Create a test instance with the temp path
    manager = ExecutionManager(epic_key)
    manager.state_dir = state_dir

    # Act
    result = manager._load_state(state_file)

    # Assert
    assert result == data


@pytest.mark.asyncio
async def test_execute_breakdown_success(mock_execution_log, mock_jira, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    epic_key = "TEST-123"
    execution_manager = ExecutionManager(epic_key)
    execution_manager.execution_log = mock_execution_log
    execution_manager.jira = mock_jira
    execution_manager.task_tracker = mock_task_tracker
    execution_manager.proposed_tickets = mock_proposed_tickets

    # Mock epic details
    mock_epic_details = JiraTicketDetails(
        key="TEST-123",
        summary="Test Epic",
        description="Test Description",
        issue_type="Epic",
        status="Open",
        project_key="TEST",
        created="2024-01-01T00:00:00.000Z",
        updated="2024-01-01T00:00:00.000Z",
        assignee="Test Assignee",
        reporter="Test Reporter",
        priority="High",
        labels=["test"],
        components=["test-component"]
    )
    
    # Mock epic analysis
    mock_analysis = AnalysisInfo(
        main_objective="Test Objective",
        technical_domains=["Domain 1"],
        core_requirements=["Req 1"],
        stakeholders=["Stakeholder 1"],
        constraints=["Constraint 1"],
        dependencies=["Dependency 1"]
    )

    # Setup async mocks
    mock_jira.get_ticket = AsyncMock(return_value=mock_epic_details)
    execution_manager.epic_analyzer.analyze_epic = AsyncMock(return_value=mock_analysis)
    execution_manager.user_story_generator.generate_user_stories = AsyncMock(return_value=[])
    execution_manager.technical_task_generator.generate_technical_tasks = AsyncMock(return_value=[])
    execution_manager.subtask_generator.break_down_tasks = AsyncMock(return_value=[])
    
    # Mock the create_execution_record as AsyncMock
    mock_execution_log.create_execution_record = AsyncMock(return_value=None)

    # Mock proposed tickets response
    mock_proposed_tickets.filename = "test_proposed_tickets.yaml"
    mock_proposed_tickets.add_high_level_task.return_value = "TEST-124"
    mock_proposed_tickets.add_subtasks.return_value = ["TEST-125"]
    mock_execution_log.filename = "test_execution_log.yaml"

    # Act
    result = await execution_manager.execute_breakdown()

    # Assert
    assert isinstance(result, EpicBreakdownResponse)
    assert result.epic_key == epic_key
    assert result.execution_id == execution_manager.execution_id
    assert result.proposed_tickets_file == mock_proposed_tickets.filename
    assert result.execution_plan_file == mock_execution_log.filename

    # Verify service calls
    mock_jira.get_ticket.assert_called_once_with(epic_key)
    execution_manager.epic_analyzer.analyze_epic.assert_called_once_with(
        mock_epic_details.summary,
        mock_epic_details.description
    )
    mock_execution_log.create_execution_record.assert_called_once()


def test_handle_task_generation_error(execution_manager):
    # Arrange
    error = Exception("Test error")
    mock_task_tracker = Mock()
    mock_task_tracker.get_summary.return_value = {
        "errors": [],
        "tasks": [],
        "total_tasks": 0
    }
    mock_epic_analysis = Mock()
    mock_epic_analysis.model_dump.return_value = {
        "main_objective": "Test",
        "technical_domains": [],
        "core_requirements": [],
        "stakeholders": []
    }
    
    execution_manager._save_state = Mock()

    # Act
    execution_manager._handle_task_generation_error(
        error,
        mock_task_tracker,
        mock_epic_analysis
    )

    # Assert
    mock_task_tracker.get_summary.assert_called_once()
    execution_manager.execution_log.log_summary.assert_called_once()
    execution_manager._save_state.assert_called_with(
        "error_state.json",
        {
            "error": "Test error",
            "task_tracker_summary": {
                "errors": ["Test error"],
                "tasks": [],
                "total_tasks": 0
            },
            "epic_analysis": {
                "main_objective": "Test",
                "technical_domains": [],
                "core_requirements": [],
                "stakeholders": []
            }
        }
    )


def test_handle_fatal_error(execution_manager):
    # Arrange
    error = Exception("Test error")

    # Act
    execution_manager._handle_fatal_error(error)

    # Assert
    execution_manager.execution_log.log_section.assert_called() 