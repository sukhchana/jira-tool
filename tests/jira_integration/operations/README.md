# JIRA Integration Tests

This directory contains tests for the JIRA integration module, focusing on the operations that interact with the JIRA API.

## Testing Approach

We have two types of tests:

### 1. Unit Tests (`test_base_operation.py`)

The unit tests attempt to mock the JIRA API calls to test the behavior of the `BaseJiraOperation` class without making actual API calls. However, due to the complexity of mocking `aiohttp.ClientSession` and its async context managers, these tests may be challenging to maintain.

**Current limitations:** Due to the async nature of `aiohttp.ClientSession`, properly mocking all the required behaviors is complex. The coroutine and async context manager handling makes it particularly challenging.

### 2. Integration Tests (`test_base_operation_integration.py`)

The integration tests connect to an actual JIRA instance using the same environment variables as the main application. These tests:

- Create real JIRA issues
- Update those issues
- Transition them between statuses
- Search for issues
- Clean up after themselves (by marking test issues as completed)

Integration tests are **skipped by default** to avoid affecting real JIRA instances during routine test runs.

## Running Integration Tests

To run the integration tests:

1. Set the required environment variables with your actual JIRA credentials:

```bash
export JIRA_SERVER="https://your-jira-instance.atlassian.net"  # Your actual JIRA instance URL
export JIRA_EMAIL="your-email@example.com"                     # Your JIRA account email
export JIRA_API_TOKEN="your-api-token"                         # Your API token
export JIRA_TEST_PROJECT="TEST"                                # Change to your test project key
export RUN_JIRA_INTEGRATION_TESTS="true"                       # Enable integration tests
```

2. Run the tests:

```bash
python -m pytest tests/jira_integration/operations/test_base_operation_integration.py -v
```

⚠️ **Warning:** Integration tests create and modify real JIRA issues. Only run them with credentials for a test JIRA instance or a project dedicated to testing.

## Best Practices

When adding new functionality to `BaseJiraOperation`:

1. Try to add unit tests first, mocking the API calls
2. If the mocking proves too complex, add integration tests instead
3. Always ensure integration tests clean up after themselves
4. Label test issues clearly so they can be identified in the JIRA instance

## Debugging Integration Tests

If you encounter issues with integration tests:

1. Verify your JIRA credentials are correct
2. Check that you have permissions to create and modify issues in the specified project
3. Ensure your JIRA instance supports the operations being tested (e.g., specific transitions)
4. Look for test issues that may have been created but not cleaned up properly 