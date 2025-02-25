import base64
import os
from typing import Dict


def get_jira_server() -> str:
    """
    Get the JIRA server URL from environment variables.
    
    Returns:
        str: The JIRA server URL
        
    Raises:
        EnvironmentError: If JIRA_SERVER environment variable is not set
    """
    jira_server = os.getenv("JIRA_SERVER")
    if not jira_server:
        raise EnvironmentError("JIRA_SERVER environment variable is not set")
    return jira_server


def get_jira_auth_headers() -> str:
    """
    Generate authentication headers for JIRA API requests.
    
    Returns:
        str: The authentication header value in the format "Basic <encoded_credentials>"
        
    Raises:
        EnvironmentError: If JIRA_EMAIL or JIRA_API_TOKEN environment variables are not set
    """
    
    jira_user = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not jira_user:
        raise EnvironmentError("JIRA_EMAIL environment variable is not set")
    
    if not jira_token:
        raise EnvironmentError("JIRA_API_TOKEN environment variable is not set")

    # Create base64 encoded auth string
    auth_string = f"{jira_user}:{jira_token}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    return f"Basic {encoded_auth}"
