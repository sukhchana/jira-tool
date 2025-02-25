import pytest
from unittest.mock import Mock, patch, AsyncMock

from models.analysis_info import AnalysisInfo
from models.complexity_analysis import ComplexityAnalysis
from models.ticket_description import TicketDescription
from breakdown.epic_analyzer import EpicAnalyzer


@pytest.fixture
def mock_execution_log():
    return Mock()


@pytest.fixture
def analyzer(mock_execution_log):
    analyzer = EpicAnalyzer(mock_execution_log)
    analyzer.llm = Mock()
    analyzer.format_fixer = Mock()
    return analyzer


@pytest.mark.asyncio
async def test_analyze_epic_success(analyzer, mock_execution_log):
    # Arrange
    summary = "Test Epic"
    description = "Test Description"
    mock_response = "LLM Response"
    mock_analysis_dict = {
        "main_objective": "Test Objective",
        "technical_domains": ["Domain1", "Domain2"],
        "core_requirements": ["Req1", "Req2"],
        "stakeholders": ["Stakeholder1"]
    }
    
    analyzer.llm.generate_content = AsyncMock(return_value=mock_response)
    with patch('breakdown.epic_analyzer.EpicAnalysisParser') as mock_parser:
        mock_parser.parse_with_format_fixing = AsyncMock(return_value=mock_analysis_dict)

        # Act
        result = await analyzer.analyze_epic(summary, description)

        # Assert
        assert isinstance(result, AnalysisInfo)
        assert result.main_objective == "Test Objective"
        assert result.technical_domains == ["Domain1", "Domain2"]
        assert result.core_requirements == ["Req1", "Req2"]
        assert result.stakeholders == ["Stakeholder1"]
        
        # Verify LLM was called with correct parameters
        analyzer.llm.generate_content.assert_called_once()
        assert analyzer.llm.generate_content.call_args[1]["temperature"] == 0.2
        assert analyzer.llm.generate_content.call_args[1]["top_p"] == 0.8
        assert analyzer.llm.generate_content.call_args[1]["top_k"] == 40


@pytest.mark.asyncio
async def test_analyze_epic_error_handling(analyzer, mock_execution_log):
    # Arrange
    summary = "Test Epic"
    description = "Test Description"
    analyzer.llm.generate_content = AsyncMock(side_effect=Exception("LLM Error"))

    # Act
    result = await analyzer.analyze_epic(summary, description)

    # Assert
    assert isinstance(result, AnalysisInfo)
    assert result.main_objective == "Error analyzing epic"
    assert result.technical_domains == []
    assert result.core_requirements == []
    assert result.stakeholders == []


@pytest.mark.asyncio
async def test_analyze_complexity_success(analyzer, mock_execution_log):
    # Arrange
    epic_summary = "Test Epic"
    epic_description = "Test Description"
    mock_response = "LLM Response"
    mock_analysis_data = {
        "analysis": "Test Analysis",
        "story_points": 5,
        "complexity_level": "High",
        "effort_estimate": "3 days",
        "technical_factors": ["Factor1"],
        "risk_factors": ["Risk1"]
    }
    
    analyzer.llm.generate_content = AsyncMock(return_value=mock_response)
    with patch('breakdown.epic_analyzer.ComplexityAnalysisParser') as mock_parser:
        mock_parser.parse = Mock(return_value=mock_analysis_data)

        # Act
        result = await analyzer.analyze_complexity(epic_summary, epic_description)

        # Assert
        assert isinstance(result, ComplexityAnalysis)
        assert result.analysis == "Test Analysis"
        assert result.raw_response == mock_response
        assert result.story_points == 5
        assert result.complexity_level == "High"
        assert result.effort_estimate == "3 days"
        assert result.technical_factors == ["Factor1"]
        assert result.risk_factors == ["Risk1"]


@pytest.mark.asyncio
async def test_generate_ticket_description_success(analyzer, mock_execution_log):
    # Arrange
    context = "Test Context"
    requirements = "Test Requirements"
    additional_info = {"key": "value"}
    mock_response = "LLM Response"
    mock_ticket = TicketDescription(
        title="Test Ticket",
        description="Test Description",
        technical_domain="Test Domain",
        required_skills=["Skill1"],
        story_points=3,
        suggested_assignee="Test Assignee",
        complexity="Medium",
        acceptance_criteria=["Criteria1"],
        scenarios=[],
        technical_notes="Test Notes"
    )
    
    analyzer.llm.generate_content = AsyncMock(return_value=mock_response)
    with patch('breakdown.epic_analyzer.TicketDescriptionParser') as mock_parser:
        mock_parser.parse = Mock(return_value=mock_ticket)

        # Act
        result = await analyzer.generate_ticket_description(
            context, requirements, additional_info
        )

        # Assert
        assert isinstance(result, TicketDescription)
        assert result.title == "Test Ticket"
        assert result.description == "Test Description"
        assert result.technical_domain == "Test Domain"
        assert result.required_skills == ["Skill1"]
        assert result.story_points == 3
        assert result.suggested_assignee == "Test Assignee"
        assert result.complexity == "Medium"
        assert result.acceptance_criteria == ["Criteria1"]
        assert result.technical_notes == "Test Notes" 