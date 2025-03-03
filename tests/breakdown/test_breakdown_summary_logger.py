import pytest
from unittest.mock import Mock, patch

from breakdown.breakdown_summary_logger import log_completion_summary


@pytest.fixture
def mock_task_tracker():
    tracker = Mock()
    tracker.get_summary.return_value = {
        "user_stories": 2,
        "technical_tasks": 3,
        "subtasks": 10,
        "subtasks_by_parent": {
            "Story 1": 3,
            "Story 2": 4,
            "Task 1": 3
        }
    }
    tracker.subtasks = {
        "Story 1": [{"story_points": 2, "required_skills": ["Python", "AWS"]}],
        "Story 2": [{"story_points": 3, "required_skills": ["React", "Node"]}],
        "Task 1": [{"story_points": 5, "required_skills": ["DevOps"]}]
    }
    return tracker


@pytest.fixture
def mock_execution_log():
    return Mock()


def test_log_completion_summary_success(mock_task_tracker, mock_execution_log):
    # Act
    log_completion_summary(mock_task_tracker, mock_execution_log)

    # Assert
    mock_execution_log.log_section.assert_called_once()
    args = mock_execution_log.log_section.call_args[0]
    assert args[0] == "Task Breakdown Completion"
    assert "Task Breakdown Completion Report" in args[1]


def test_log_completion_summary_empty_tasks(mock_task_tracker, mock_execution_log):
    # Arrange
    mock_summary = {
        'user_stories': 0,
        'technical_tasks': 0,
        'subtasks': 0,
        'subtasks_by_parent': {}
    }
    
    mock_task_tracker.get_summary.return_value = mock_summary
    mock_task_tracker.subtasks = {}

    # Act
    log_completion_summary(mock_task_tracker, mock_execution_log)

    # Assert
    mock_task_tracker.get_summary.assert_called_once()
    mock_execution_log.log_section.assert_called_once()
    
    # Verify the content of the log
    log_call = mock_execution_log.log_section.call_args
    log_content = log_call[0][1]
    
    # Check key statistics in the log content
    assert "Total tasks processed: 0" in log_content
    assert "User Stories: 0" in log_content
    assert "Technical Tasks: 0" in log_content
    assert "Total subtasks created: 0" in log_content
    assert "Total story points: 0" in log_content


def test_log_completion_summary_error_handling(mock_task_tracker, mock_execution_log):
    # Arrange
    mock_task_tracker.get_summary.side_effect = Exception("Test error")

    # Act
    with pytest.raises(Exception) as exc:
        log_completion_summary(mock_task_tracker, mock_execution_log)

    # Assert
    assert str(exc.value) == "Test error"
    mock_execution_log.log_section.assert_not_called() 