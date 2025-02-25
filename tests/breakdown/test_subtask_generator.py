import pytest
from unittest.mock import Mock, patch, AsyncMock

from models.sub_task import SubTask
from models.user_story import UserStory
from models.technical_task import TechnicalTask
from models.story_description import StoryDescription
from models.implementation_notes import ImplementationNotes
from breakdown.subtask_generator import SubtaskGenerator
from models.jira_ticket_details import JiraTicketDetails


@pytest.fixture
def mock_execution_log():
    return Mock()


@pytest.fixture
def generator(mock_execution_log):
    generator = SubtaskGenerator(mock_execution_log)
    generator.llm = Mock()
    generator.execution_log = mock_execution_log
    return generator


@pytest.fixture
def mock_task_tracker():
    return Mock()


@pytest.fixture
def mock_proposed_tickets():
    return Mock()


@pytest.fixture
def mock_user_story():
    return UserStory(
        id="US-1",
        title="Test User Story",
        type="User Story",
        description=StoryDescription(
            role="developer",
            goal="implement feature",
            benefit="improve system",
            formatted="As a developer, I want to implement feature, so that I can improve system"
        ),
        technical_domain="Test Domain",
        complexity="Medium",
        business_value="Medium",
        story_points=3,
        required_skills=["Skill1"],
        suggested_assignee="Test Assignee",
        dependencies=[],
        acceptance_criteria=["Criteria1"],
        implementation_notes=ImplementationNotes()
    )


@pytest.fixture
def mock_technical_task():
    return TechnicalTask(
        id="TT-1",
        title="Test Technical Task",
        type="Technical Task",
        description="Test Description",
        technical_domain="Test Domain",
        complexity="Medium",
        business_value="Medium",
        story_points=3,
        required_skills=["Skill1"],
        suggested_assignee="Test Assignee",
        dependencies=[],
        implementation_approach={
            "approach": "Test approach",
            "architecture": "Test architecture",
            "data_flow": "Test data flow",
            "security": "Test security",
            "dependencies": "Test dependencies"
        },
        acceptance_criteria=["Test Criteria"],
        performance_impact="Low impact",
        scalability_considerations="Scales well",
        monitoring_needs="Basic monitoring",
        testing_requirements="Unit tests required"
    )


@pytest.fixture
def mock_subtask():
    return SubTask(
        id="ST-1",
        parent_id="US-1",
        title="Test Subtask",
        type="Sub-task",
        description="Test Description",
        technical_domain="Test Domain",
        complexity="Medium",
        business_value="Medium",
        story_points=2,
        required_skills=["Skill1"],
        suggested_assignee="Test Assignee",
        dependencies=[],
        acceptance_criteria=["Test Criteria"]
    )


@pytest.mark.asyncio
@patch('breakdown.subtask_generator.SubtaskParser')
async def test_break_down_tasks_success(mock_parser, generator, mock_user_story, mock_technical_task, mock_subtask, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    high_level_tasks = [
        mock_user_story,
        TechnicalTask(
            id="TT-1",
            title="Test Technical Task",
            type="Technical Task",
            description="Test Description",
            technical_domain="Test Domain",
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
                "dependencies": "Test dependencies"
            }
        )
    ]
    epic_details = {
        "key": "EPIC-1",
        "summary": "Test Epic",
        "description": "Test Description",
        "issue_type": "Epic",
        "status": "Open",
        "project_key": "TEST",
        "created": "2024-01-01T00:00:00.000Z",
        "updated": "2024-01-01T00:00:00.000Z"
    }
    
    # Mock the parser to return our mock subtask
    mock_parser.parse = Mock(return_value=[mock_subtask])
    
    # Mock LLM responses for enrichment methods
    generator.llm.generate_content = AsyncMock(return_value='{"test": "response"}')
    
    # Mock the enrichment methods
    generator._generate_implementation_approach = AsyncMock(return_value={"approach": "test"})
    generator._generate_code_examples = AsyncMock(return_value=[{"code": "test"}])
    generator._generate_testing_plan = AsyncMock(return_value={"tests": ["test"]})
    generator._generate_research_summary = AsyncMock(return_value={"research": "test"})

    # Act
    result = await generator.break_down_tasks(
        high_level_tasks,
        epic_details,
        mock_task_tracker,
        mock_proposed_tickets
    )

    # Assert
    assert len(result) == 2  # One subtask per high-level task
    assert isinstance(result[0], SubTask)
    assert result[0].id == mock_subtask.id
    assert result[0].title == mock_subtask.title
    
    # Verify tracking calls
    mock_task_tracker.add_subtasks.assert_called()
    mock_proposed_tickets.add_subtasks.assert_called()


@pytest.mark.asyncio
async def test_break_down_tasks_empty_tasks(generator, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    high_level_tasks = []
    epic_details = {"key": "EPIC-1", "summary": "Test Epic"}

    # Act
    result = await generator.break_down_tasks(
        high_level_tasks,
        epic_details,
        mock_task_tracker,
        mock_proposed_tickets
    )

    # Assert
    assert len(result) == 0
    mock_task_tracker.add_subtasks.assert_not_called()
    mock_proposed_tickets.add_subtasks.assert_not_called()


@pytest.mark.asyncio
@patch('breakdown.subtask_generator.SubtaskParser')
async def test_break_down_tasks_llm_error(mock_parser, generator, mock_user_story, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    high_level_tasks = [mock_user_story]
    epic_details = {"key": "EPIC-1", "summary": "Test Epic"}
    
    # Mock LLM error
    generator.llm.generate_content = AsyncMock(side_effect=Exception("LLM error"))

    # Act & Assert
    with pytest.raises(Exception) as context:
        await generator.break_down_tasks(
            high_level_tasks,
            epic_details,
            mock_task_tracker,
            mock_proposed_tickets
        )
    assert "LLM error" in str(context.value)


@pytest.mark.asyncio
@patch('breakdown.subtask_generator.SubtaskParser')
async def test_break_down_tasks_parsing_error(mock_parser, generator, mock_user_story, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    high_level_tasks = [mock_user_story]
    epic_details = {"key": "EPIC-1", "summary": "Test Epic"}
    
    generator.llm.generate_content = AsyncMock(return_value='{"test": "response"}')
    mock_parser.parse = Mock(side_effect=ValueError("Parsing error"))

    # Act & Assert
    with pytest.raises(ValueError) as context:
        await generator.break_down_tasks(
            high_level_tasks,
            epic_details,
            mock_task_tracker,
            mock_proposed_tickets
        )
    assert "Parsing error" in str(context.value)


@pytest.mark.asyncio
@patch('breakdown.subtask_generator.SubtaskParser')
async def test_break_down_tasks_tracking_error(mock_parser, generator, mock_user_story, mock_subtask, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    high_level_tasks = [mock_user_story]
    epic_details = JiraTicketDetails(
        key="EPIC-1",
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
    ).model_dump()  # Convert to dictionary
    
    mock_parser.return_value.parse.return_value = [mock_subtask]
    generator.llm.generate_content = AsyncMock(return_value='{"test": "response"}')
    
    # Mock tracking error
    mock_task_tracker.add_subtasks.side_effect = Exception("Tracking error")

    # Act & Assert
    with pytest.raises(Exception) as context:
        await generator.break_down_tasks(
            high_level_tasks,
            epic_details,
            mock_task_tracker,
            mock_proposed_tickets
        )
    assert "Tracking error" in str(context.value)


@pytest.mark.asyncio
@patch('breakdown.subtask_generator.settings')
async def test_generate_implementation_approach_disabled(mock_settings, generator):
    # Arrange
    mock_settings.ENABLE_IMPLEMENTATION_APPROACH = False
    subtask_context = {"title": "Test Subtask"}

    # Act
    result = await generator._generate_implementation_approach(subtask_context)

    # Assert
    assert result == {}
    generator.llm.generate_content.assert_not_called()


def test_combine_description(generator):
    # Arrange
    base_description = "Base description"
    additional_content = "Additional content"

    # Act
    result = generator._combine_description(base_description, additional_content)

    # Assert
    assert result == "Base description\n\nAdditional content"


def test_format_code_examples(generator):
    # Arrange
    code_examples = [
        {
            "description": "Test Example",
            "language": "python",
            "code": "def test(): pass"
        }
    ]

    # Act
    result = generator._format_code_examples(code_examples)

    # Assert
    expected = "### Test Example\n```python\ndef test(): pass\n```\n"
    assert result == expected


def test_extract_test_criteria(generator):
    # Arrange
    testing_plan = {
        "unit_tests": ["Test unit functionality"],
        "integration_tests": ["Test integration"],
        "edge_cases": ["Handle null input"]
    }

    # Act
    result = generator._extract_test_criteria(testing_plan)

    # Assert
    expected = [
        "Unit Test: Test unit functionality",
        "Integration Test: Test integration",
        "Edge Case: Handle null input"
    ]
    assert result == expected


def test_format_research_summary(generator):
    # Arrange
    research = {
        "pain_points": "Test challenges",
        "success_metrics": "Test metrics",
        "modern_approaches": "Test approaches",
        "performance_considerations": "Test performance",
        "security_implications": "Test security"
    }

    # Act
    result = generator._format_research_summary(research)

    # Assert
    assert "**Technical Challenges:**\nTest challenges" in result
    assert "**Success Metrics:**\nTest metrics" in result
    assert "**Implementation Approach:**\nTest approaches" in result
    assert "**Performance Considerations:**\nTest performance" in result
    assert "**Security Considerations:**\nTest security" in result 