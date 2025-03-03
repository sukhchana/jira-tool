import pytest
from unittest.mock import Mock, patch, AsyncMock

from models.user_story import UserStory
from models.research_summary import ResearchSummary
from models.code_block import CodeBlock
from models.gherkin import GherkinScenario, GherkinStep
from models.story_description import StoryDescription
from models.implementation_notes import ImplementationNotes
from breakdown.user_story_generator import UserStoryGenerator


@pytest.fixture
def mock_execution_log():
    return Mock()


@pytest.fixture
def generator(mock_execution_log):
    generator = UserStoryGenerator(mock_execution_log)
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
def mock_epic_analysis():
    return {
        "main_objective": "Test Objective",
        "technical_domains": ["Domain 1", "Domain 2"],
        "core_requirements": ["Req 1", "Req 2"],
        "stakeholders": ["Stakeholder 1"]
    }


@pytest.mark.asyncio
@patch('breakdown.user_story_generator.UserStoryParser')
async def test_generate_user_stories_success(mock_parser, generator, mock_task_tracker, mock_proposed_tickets, mock_epic_analysis):
    # Arrange
    mock_response = "LLM Response"
    mock_stories = [
        {
            "id": "US-1",
            "title": "Test Story 1",
            "type": "User Story",
            "description": StoryDescription(
                role="developer",
                goal="implement feature",
                benefit="improve system",
                formatted="As a developer, I want to implement feature, so that I can improve system"
            ),
            "technical_domain": "Domain 1",
            "complexity": "Medium",
            "business_value": "High",
            "story_points": 3,
            "required_skills": ["Skill1"],
            "suggested_assignee": "Test Assignee",
            "dependencies": [],
            "acceptance_criteria": ["Criteria1"],
            "implementation_notes": ImplementationNotes()
        }
    ]
    
    generator.llm.generate_content = AsyncMock(return_value=mock_response)
    mock_parser.parse_from_response = Mock(return_value=mock_stories)
    
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
                steps=[
                    GherkinStep(keyword="Given", text="a test condition"),
                    GherkinStep(keyword="When", text="an action is taken"),
                    GherkinStep(keyword="Then", text="a result is observed")
                ]
            )
        ]
    )

    # Mock proposed tickets service to return story ID
    mock_proposed_tickets.add_high_level_task = Mock(return_value="US-1")

    # Act
    result = await generator.generate_user_stories(
        mock_epic_analysis,
        mock_task_tracker,
        mock_proposed_tickets
    )

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], UserStory)
    assert result[0].title == "Test Story 1"
    assert result[0].id == "US-1"
    
    # Verify service calls
    mock_task_tracker.add_user_story.assert_called_once()
    mock_proposed_tickets.add_high_level_task.assert_called_once()
    generator.execution_log.log_llm_interaction.assert_called()


@pytest.mark.asyncio
async def test_generate_user_stories_empty_epic_analysis(generator, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    epic_analysis = {"main_objective": "", "technical_domains": [], "core_requirements": []}
    generator.llm.generate_content = AsyncMock(return_value="")
    generator.execution_log.log_section = Mock()

    # Act
    result = await generator.generate_user_stories(epic_analysis, mock_task_tracker, mock_proposed_tickets)

    # Assert
    assert len(result) == 0
    generator.execution_log.log_section.assert_called_once_with(
        "User Story Generation",
        "No user stories generated: Empty epic analysis"
    )


@pytest.mark.asyncio
@patch('breakdown.user_story_generator.UserStoryParser')
async def test_generate_user_stories_llm_error(mock_parser, generator, mock_task_tracker, mock_proposed_tickets, mock_epic_analysis):
    # Arrange
    generator.llm.generate_content = AsyncMock(
        side_effect=Exception("LLM error")
    )

    # Act & Assert
    with pytest.raises(Exception) as context:
        await generator.generate_user_stories(
            mock_epic_analysis,
            mock_task_tracker,
            mock_proposed_tickets
        )
    assert "LLM error" in str(context.value)


@pytest.mark.asyncio
@patch('breakdown.user_story_generator.UserStoryParser')
async def test_generate_user_stories_parsing_error(mock_parser, generator, mock_task_tracker, mock_proposed_tickets, mock_epic_analysis):
    # Arrange
    mock_response = "Invalid Response"
    generator.llm.generate_content = AsyncMock(return_value=mock_response)
    mock_parser.parse_from_response = Mock(side_effect=ValueError("Parsing error"))

    # Act & Assert
    with pytest.raises(ValueError) as context:
        await generator.generate_user_stories(
            mock_epic_analysis,
            mock_task_tracker,
            mock_proposed_tickets
        )
    assert "Parsing error" in str(context.value)


@pytest.mark.asyncio
@patch('breakdown.user_story_generator.settings')
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
@patch('breakdown.user_story_generator.settings')
async def test_generate_research_summary_error(mock_settings, generator):
    # Arrange
    mock_settings.ENABLE_RESEARCH_TASKS = True
    story_context = {"title": "Test Story"}
    generator.llm.generate_content = AsyncMock(
        side_effect=Exception("Research generation error")
    )

    # Act & Assert
    with pytest.raises(Exception) as context:
        await generator._generate_research_summary(story_context)
    assert "Research generation error" in str(context.value)


@pytest.mark.asyncio
@patch('breakdown.user_story_generator.settings')
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
@patch('breakdown.user_story_generator.settings')
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
async def test_generate_user_stories_error_handling(generator, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    epic_analysis = {"main_objective": "Test", "technical_domains": ["Domain1"]}
    generator.llm.generate_content = AsyncMock(side_effect=Exception("Test error"))
    generator.execution_log.log_llm_interaction = Mock()

    # Act & Assert
    with pytest.raises(Exception) as exc:
        await generator.generate_user_stories(epic_analysis, mock_task_tracker, mock_proposed_tickets)

    assert str(exc.value) == "Test error"
    generator.execution_log.log_llm_interaction.assert_called_once_with(
        "User Story Generation",
        None,  # No response since an error occurred
        "Test error"
    )


@pytest.mark.asyncio
@patch('breakdown.user_story_generator.UserStoryParser')
async def test_generate_user_stories_with_invalid_story_data(mock_parser, generator, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    epic_analysis = {
        "main_objective": "Test",
        "technical_domains": ["Domain1"],
        "core_requirements": ["Req1"],
        "stakeholders": ["Stakeholder1"],
        "constraints": ["Constraint1"],
        "dependencies": ["Dependency1"]
    }
    
    # Mock LLM response with invalid data
    generator.llm.generate_content = AsyncMock(return_value='{"invalid": "data"}')
    
    # Setup parser to raise ValueError
    mock_parser.parse_from_response = Mock(side_effect=ValueError("Invalid story data"))
    
    # Act
    with pytest.raises(ValueError) as exc_info:
        await generator.generate_user_stories(epic_analysis, mock_task_tracker, mock_proposed_tickets)
    
    # Assert
    assert str(exc_info.value) == "Invalid story data"
    
    # Verify section logging was called
    generator.execution_log.log_section.assert_called_once_with(
        "User Story Generation Error",
        "Failed to parse user stories from LLM response"
    )
    
    # Note: For parsing errors, log_llm_interaction is NOT called based on the implementation
    # so we verify it was NOT called
    generator.execution_log.log_llm_interaction.assert_not_called()


@pytest.mark.asyncio
@patch('breakdown.user_story_generator.UserStoryParser')
async def test_generate_user_stories_with_tracking_error(mock_parser, generator, mock_task_tracker, mock_proposed_tickets):
    # Arrange
    epic_analysis = {
        "main_objective": "Test",
        "technical_domains": ["Domain1"],
        "core_requirements": ["Req1"],
        "stakeholders": ["Stakeholder1"],
        "constraints": ["Constraint1"],
        "dependencies": ["Dependency1"]
    }
    
    # Create a valid story
    mock_story = {
        "title": "Test Story",
        "type": "User Story",
        "description": {
            "role": "developer",
            "goal": "implement feature",
            "benefit": "improve system",
            "formatted": "As a developer, I want to implement feature, so that I can improve system"
        },
        "technical_domain": "Domain1",
        "complexity": "Medium",
        "business_value": "High",
        "story_points": 3,
        "required_skills": ["Skill1"],
        "suggested_assignee": "Test Assignee",
        "dependencies": [],
        "acceptance_criteria": ["Criteria1"],
        "implementation_notes": {}
    }
    
    # Setup mocks
    generator.llm.generate_content = AsyncMock(return_value='{"valid": "story"}')
    mock_parser.parse_from_response = Mock(return_value=[mock_story])
    mock_task_tracker.add_user_story = Mock(side_effect=Exception("Tracking error"))
    
    # Act & Assert
    with pytest.raises(Exception) as exc:
        await generator.generate_user_stories(epic_analysis, mock_task_tracker, mock_proposed_tickets)
    
    assert str(exc.value) == "Tracking error"
    
    # Verify the story was attempted to be tracked
    mock_task_tracker.add_user_story.assert_called_once()
    
    # Verify error was logged
    generator.execution_log.log_llm_interaction.assert_called() 