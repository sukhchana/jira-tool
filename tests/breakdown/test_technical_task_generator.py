import pytest
from unittest.mock import Mock, patch, AsyncMock

from models.technical_task import TechnicalTask
from models.user_story import UserStory
from models.research_summary import ResearchSummary
from models.code_block import CodeBlock
from models.gherkin import GherkinScenario
from models.story_description import StoryDescription
from models.implementation_notes import ImplementationNotes
from breakdown.technical_task_generator import TechnicalTaskGenerator


@pytest.fixture
def mock_execution_log():
    return Mock()


@pytest.fixture
def generator(mock_execution_log):
    generator = TechnicalTaskGenerator(mock_execution_log)
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
def mock_user_stories():
    return [
        UserStory(
            title="Test Story 1",
            type="User Story",
            description=StoryDescription(
                role="developer",
                goal="implement feature",
                benefit="improve system",
                formatted="As a developer, I want to implement feature, so that I can improve system"
            ),
            technical_domain="Domain 1",
            complexity="Medium",
            business_value="Medium",
            story_points=3,
            required_skills=["Skill1"],
            suggested_assignee="Test Assignee",
            dependencies=[],
            acceptance_criteria=["Criteria1"],
            implementation_notes=ImplementationNotes()
        ),
        UserStory(
            title="Test Story 2",
            type="User Story",
            description=StoryDescription(
                role="user",
                goal="use feature",
                benefit="get value",
                formatted="As a user, I want to use feature, so that I can get value"
            ),
            technical_domain="Domain 2",
            complexity="High",
            business_value="High",
            story_points=5,
            required_skills=["Skill2"],
            suggested_assignee="Test Assignee",
            dependencies=[],
            acceptance_criteria=["Criteria2"],
            implementation_notes=ImplementationNotes()
        )
    ]


@pytest.fixture
def mock_epic_analysis():
    return {
        "main_objective": "Test Objective",
        "technical_domains": ["Domain 1", "Domain 2"],
        "core_requirements": ["Req 1", "Req 2"]
    }


@pytest.mark.asyncio
@patch('breakdown.technical_task_generator.TechnicalTaskParser')
async def test_generate_technical_tasks_success(mock_parser, generator, mock_user_stories, mock_epic_analysis, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    mock_response = "LLM Response"
    mock_tasks = [
        {
            "id": "TT-1",
            "title": "Test Task 1",
            "type": "Technical Task",
            "description": "Test Description 1",
            "technical_domain": "Domain 1",
            "complexity": "Medium",
            "business_value": "Medium",
            "story_points": 3,
            "required_skills": ["Skill1"],
            "suggested_assignee": "Test Assignee",
            "dependencies": [],
            "acceptance_criteria": ["Test Criteria"],
            "performance_impact": "Low impact",
            "scalability_considerations": "Scales well",
            "monitoring_needs": "Basic monitoring",
            "testing_requirements": "Unit tests required",
            "implementation_approach": {
                "approach": "Test approach",
                "architecture": "Test architecture",
                "data_flow": "Test data flow",
                "security": "Test security",
                "dependencies": "Test dependencies"
            }
        }
    ]
    
    generator.llm.generate_content = AsyncMock(return_value=mock_response)
    mock_parser.parse_from_response = Mock(return_value=mock_tasks)
    
    # Mock additional component generation methods
    generator._generate_research_summary = AsyncMock(
        return_value=ResearchSummary(
            pain_points="Test Pain Points",
            success_metrics="Test Metrics",
            similar_implementations="Test Similar",
            modern_approaches="Test Modern"
        )
    )
    generator._generate_code_examples = AsyncMock(
        return_value=[
            CodeBlock(
                language="python",
                description="Test Code",
                code="def test(): pass"
            )
        ]
    )
    generator._generate_gherkin_scenarios = AsyncMock(
        return_value=[
            GherkinScenario(
                name="Test Scenario",
                steps=[]
            )
        ]
    )

    # Mock proposed tickets service to return task ID
    mock_proposed_tickets.add_high_level_task = Mock(return_value="TT-1")

    # Act
    result = await generator.generate_technical_tasks(
        mock_user_stories,
        mock_epic_analysis,
        mock_task_tracker,
        mock_proposed_tickets
    )

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], TechnicalTask)
    assert result[0].title == "Test Task 1"
    assert result[0].id == "TT-1"
    
    # Verify service calls
    mock_task_tracker.add_technical_task.assert_called_once()
    mock_proposed_tickets.add_high_level_task.assert_called_once()
    generator.execution_log.log_llm_interaction.assert_called()


@pytest.mark.asyncio
@patch('breakdown.technical_task_generator.settings')
async def test_generate_research_summary_disabled(mock_settings, generator):
    # Arrange
    mock_settings.ENABLE_RESEARCH_TASKS = False
    story_context = {"title": "Test Story"}

    # Act
    result = await generator._generate_research_summary(story_context)

    # Assert
    assert isinstance(result, ResearchSummary)
    generator.llm.generate_content.assert_not_called()


@pytest.mark.asyncio
@patch('breakdown.technical_task_generator.settings')
async def test_generate_code_examples_disabled(mock_settings, generator):
    # Arrange
    mock_settings.ENABLE_CODE_BLOCK_GENERATION = False
    story_context = {"title": "Test Story"}

    # Act
    result = await generator._generate_code_examples(story_context)

    # Assert
    assert result == []
    generator.llm.generate_content.assert_not_called()


@pytest.mark.asyncio
@patch('breakdown.technical_task_generator.settings')
async def test_generate_gherkin_scenarios_disabled(mock_settings, generator):
    # Arrange
    mock_settings.ENABLE_GHERKIN_SCENARIOS = False
    story_context = {"title": "Test Story"}

    # Act
    result = await generator._generate_gherkin_scenarios(story_context)

    # Assert
    assert result == []
    generator.llm.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_generate_technical_tasks_error_handling(
    generator: TechnicalTaskGenerator,
    mock_task_tracker,
    mock_proposed_tickets,
    mock_execution_log
):
    """Test that LLM errors are properly logged and handled"""
    # Setup
    test_error = Exception("Test LLM error")
    generator.llm.generate_content.side_effect = test_error
    
    user_stories = [
        UserStory(
            title="Test Story",
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
            implementation_notes=ImplementationNotes(),
            type="User Story"
        )
    ]
    epic_analysis = {
        "main_objective": "Test objective",
        "technical_domains": ["Domain 1"],
        "core_requirements": ["Req 1"],
        "stakeholders": ["Stakeholder 1"],
        "constraints": ["Test constraint"],
        "dependencies": ["Test dependency"]
    }

    # Execute and verify
    result = await generator.generate_technical_tasks(
        user_stories,
        epic_analysis,
        mock_task_tracker,
        mock_proposed_tickets
    )
    
    # Verify the method returned an empty list
    assert result == []
    
    # Verify logging occurred before returning
    mock_execution_log.log_llm_interaction.assert_called_once_with(
        "Technical Task Generation",
        None,
        "Test LLM error"
    ) 