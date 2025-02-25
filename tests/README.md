# JIRA Integration Tests

This directory contains tests for the JIRA integration module. Tests are organized into unit tests and integration tests.

## Test Structure

The test structure mirrors the structure of the `jira_integration` module:

```
tests/
│
├── jira_integration/
│   ├── operations/
│   │   ├── test_base_operation.py
│   │   ├── test_epic_operations.py
│   │   ├── test_ticket_operations.py
│   │
│   ├── test_jira_service.py
│   ├── test_jira_auth_helper.py
│   ├── test_integration.py
│   └── conftest.py
│
└── conftest.py
```

## Running the Tests

### Prerequisites

Ensure you have all the required dependencies installed:

```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

### Running All Tests

To run all tests, use:

```bash
pytest
```

### Running Only Unit Tests

To run only unit tests (excluding integration tests):

```bash
pytest -m "not integration"
```

### Running Only Integration Tests

To run only integration tests:

```bash
pytest -m "integration"
```

### Running Tests with Coverage Report

To generate a coverage report:

```bash
pytest --cov=jira_integration
```

For a more detailed coverage report as HTML:

```bash
pytest --cov=jira_integration --cov-report=html
```

This will create an `htmlcov` directory with an HTML report of the coverage.

## Test Environment

The tests use environment variables for JIRA configuration. For unit tests, these are automatically set in `conftest.py`. For integration tests against a real JIRA instance, you should set the following environment variables:

```
JIRA_SERVER=https://your-jira-instance.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
```

## Adding New Tests

When adding new tests:

1. Follow the existing structure to place the test file in the right location
2. Use the base fixtures provided in the `conftest.py` files
3. Mark integration tests with `@pytest.mark.integration`
4. Follow the "Arrange, Act, Assert" pattern for test organization
5. For async tests, use the `@pytest.mark.asyncio` decorator 