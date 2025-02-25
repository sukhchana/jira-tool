import pytest

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

# Remove the custom event_loop fixture as it's deprecated
# and instead use the built-in one from pytest-asyncio
# The loop scope is now configured in pytest.ini 