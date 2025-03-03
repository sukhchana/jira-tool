# Running Tests

This document explains how to run the test suite for the JIRA Epic Breakdown Tool.

## Prerequisites

Before running the tests, ensure you have:

1. Python 3.8 or higher installed
2. All dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```
3. Environment variables set up (for integration tests):
   ```bash
   export JIRA_SERVER="your_jira_server"
   export JIRA_EMAIL="your_email"
   export JIRA_API_TOKEN="your_api_token"
   ```

## Test Structure

The test suite is organized by modules:

```
tests/
├── breakdown/
│   ├── test_epic_analyzer.py
│   ├── test_execution_manager.py
│   ├── test_rerun_helper.py
│   ├── test_subtask_generator.py
│   ├── test_technical_task_generator.py
│   ├── test_user_story_generator.py
│   └── test_breakdown_summary_logger.py
├── revisions/
│   ├── test_change_handler.py
│   └── test_revision_manager.py
└── services/
    ├── test_jira_service.py
    ├── test_mongodb_service.py
    └── test_proposed_tickets_service.py
```

## Running Tests

### Running All Tests

To run the entire test suite:

```bash
python -m pytest tests/
```

### Running Tests for a Specific Module

To run tests for a specific module:

```bash
python -m pytest tests/breakdown/test_epic_analyzer.py
```

### Running Tests with Coverage

To run tests with coverage reporting:

```bash
python -m pytest --cov=. tests/
```

To generate an HTML coverage report:

```bash
python -m pytest --cov=. --cov-report=html tests/
```

The HTML report will be available in the `htmlcov` directory.

## Test Categories

### Unit Tests

Located in each module's test file, these test individual components in isolation:

- `test_epic_analyzer.py`: Tests epic analysis and complexity assessment
- `test_user_story_generator.py`: Tests user story generation and enrichment
- `test_technical_task_generator.py`: Tests technical task generation
- `test_subtask_generator.py`: Tests subtask breakdown
- `test_rerun_helper.py`: Tests rerun functionality
- `test_breakdown_summary_logger.py`: Tests logging functionality

### Integration Tests

Test interactions between components:

- `test_execution_manager.py`: Tests the complete breakdown process
- `test_revision_manager.py`: Tests revision handling
- `test_jira_service.py`: Tests JIRA integration

### Mock Usage

The tests use `unittest.mock` extensively to isolate components:

- `Mock`: For synchronous method mocking
- `AsyncMock`: For asynchronous method mocking
- `patch`: For patching modules and classes

Example:
```python
@patch('breakdown.epic_analyzer.EpicAnalysisParser')
async def test_analyze_epic_success(self, mock_parser):
    # Test implementation
```

## Test Configuration

### pytest.ini

The project includes a `pytest.ini` configuration:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Fixtures

Common test fixtures are available in `tests/conftest.py`:

- `mock_llm`: Provides a mock LLM service
- `mock_jira`: Provides a mock JIRA service
- `mock_mongodb`: Provides a mock MongoDB service

## Writing New Tests

When adding new tests:

1. Follow the existing naming convention: `test_*.py`
2. Use appropriate mocks for external dependencies
3. Include both success and failure scenarios
4. Add docstrings explaining test purpose
5. Follow the Arrange-Act-Assert pattern

Example:
```python
async def test_new_feature_success(self):
    """Test successful execution of new feature."""
    # Arrange
    input_data = {"key": "value"}
    
    # Act
    result = await self.component.new_feature(input_data)
    
    # Assert
    self.assertEqual(result.status, "success")
```

## Debugging Tests

### Using pdb

To debug tests using pdb:

```bash
python -m pytest tests/path/to/test.py --pdb
```

### Using pytest-xdist

To run tests in parallel:

```bash
python -m pytest -n auto tests/
```

## Continuous Integration

Tests are automatically run in CI/CD pipelines:

1. On pull requests to main branch
2. On direct pushes to main branch
3. Nightly runs for all tests

### CI Configuration

The CI pipeline:

1. Sets up Python environment
2. Installs dependencies
3. Runs tests with coverage
4. Reports results to PR/commit status

## Common Issues

1. **Async Test Failures**
   - Ensure `asyncio_mode = auto` in pytest.ini
   - Use `async def` for test methods
   - Use `AsyncMock` for async dependencies

2. **Mock Issues**
   - Verify mock setup in setUp method
   - Check mock call assertions
   - Use appropriate mock side_effects

3. **Environment Issues**
   - Verify environment variables
   - Check Python version compatibility
   - Validate dependency versions

## Getting Help

For test-related issues:

1. Check the test logs
2. Review test documentation
3. Consult the development team
4. Open an issue in the repository 