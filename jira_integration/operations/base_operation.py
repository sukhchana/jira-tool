import os
from typing import Dict, Any, Optional, List, Union
import aiohttp
import ssl
from http import HTTPStatus
import asyncio

from dotenv import load_dotenv
from loguru import logger

from jira_integration.jira_auth_helper import get_jira_auth_headers
from models.jira_ticket_creation import JiraTicketCreation

# Load environment variables
load_dotenv()


class BaseJiraOperation:
    """
    Base class for JIRA operations with common functionality.
    
    This class provides core methods for interacting with the JIRA REST API, including
    authentication, issue retrieval, creation, updating, and searching. All specialized
    JIRA operation classes should inherit from this class.
    
    The class uses aiohttp for asynchronous HTTP requests and implements proper error
    handling and logging for all API interactions.
    """

    def __init__(self):
        """
        Initialize the JIRA REST API client.
        
        Sets up the necessary authentication headers, API base URL, and SSL context
        for communicating with the JIRA REST API. Environment variables are loaded
        to configure the client.
        """
        self._initialize_jira()
        self._epic_link_field = None  # Will be populated when needed

    def _initialize_jira(self) -> None:
        """
        Initialize JIRA REST API client with credentials from environment variables.
        
        Retrieves JIRA connection details from environment variables and configures
        the REST API client. Sets up authentication headers using Basic Auth with
        the provided email and API token.
        
        Environment variables used:
            - JIRA_SERVER: The base URL of the JIRA instance
            - JIRA_EMAIL: The email address for authentication
            - JIRA_API_TOKEN: The API token for authentication
            
        Raises:
            ValueError: If any required environment variable is missing
            Exception: If initialization fails for any other reason
        """
        try:
            self.jira_url = os.getenv("JIRA_SERVER")
            self.api_base_url = f"{self.jira_url}/rest/api/latest"

            if not all([self.jira_url]):
                raise ValueError(
                    "Missing required JIRA environment variables. "
                    "Please ensure JIRA_SERVER, JIRA_EMAIL, and JIRA_API_TOKEN are set."
                )

            self.headers = {
                "Authorization": f"{get_jira_auth_headers()}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Create SSL context that ignores certificate validation
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

        except Exception as e:
            logger.error(f"Failed to initialize JIRA client: {str(e)}")
            raise

    async def _get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a JIRA issue by its key using the REST API.
        
        Makes an asynchronous HTTP GET request to the JIRA REST API to fetch an issue's
        details. The response is transformed into a standardized dictionary format
        with consistent field naming, regardless of the specific JIRA instance configuration.
        
        Args:
            issue_key (str): The JIRA issue key (e.g., "PROJECT-123")
            
        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the issue details in a standardized
                                     format, or None if the issue cannot be retrieved or processed
                                     
        Raises:
            Exception: If there's a network error or other unexpected failure
            
        The returned dictionary includes:
            - key: The issue key
            - summary: The issue summary/title
            - description: The issue description
            - status: Object containing status information
            - issuetype: Object containing issue type information
            - project: Object containing project information
            - created/updated: Timestamps for issue creation and updates
            - assignee/reporter: User information
            - labels/components: Lists of related metadata
            - Various custom fields: Any additional JIRA custom fields present
        """
        try:
            logger.info(f"Making JIRA API call to fetch issue: {issue_key}")

            url = f"{self.api_base_url}/issue/{issue_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers,
                    ssl=self.ssl_context
                ) as response:
                    if response.status != HTTPStatus.OK:
                        logger.error(f"Failed to get issue {issue_key}: Status {response.status}")
                        logger.error(f"Response: {await response.text()}")
                        return None

                    issue_data = await response.json()
                    
            # Extract basic issue data from the REST API response
            try:
                # Check if the response is already in a flattened format or has a 'fields' object
                if "fields" in issue_data:
                    # Standard JIRA API format with 'fields' object
                    fields = issue_data["fields"]
                    
                    # Map REST API response to our standardized structure
                    result = {
                        "key": issue_data["key"],
                        "fields": {
                            "summary": fields["summary"],
                            "description": fields["description"] or "",
                            "status": fields["status"],
                            "issuetype": fields["issuetype"],
                            "project": fields["project"],
                            "created": fields.get("created"),
                            "updated": fields.get("updated"),
                            "assignee": fields.get("assignee"),
                            "reporter": fields.get("reporter"),
                            "priority": fields.get("priority"),
                            "labels": fields.get("labels", []),
                            "components": fields.get("components", [])
                        }
                    }
                    
                    # Add parent if exists (for subtasks)
                    if "parent" in fields:
                        result["fields"]["parent"] = fields["parent"]
                    
                    # Add epic link if exists
                    if "customfield_10014" in fields:
                        result["fields"]["customfield_10014"] = fields["customfield_10014"]
                    
                    # Add story points if exists
                    if "customfield_10016" in fields:
                        result["fields"]["customfield_10016"] = fields["customfield_10016"]
                    
                    # Add any other custom fields
                    for field_name, field_value in fields.items():
                        if field_name.startswith("customfield_") and field_value is not None and field_name not in ["customfield_10014", "customfield_10016"]:
                            result["fields"][field_name] = field_value
                else:
                    # Flattened format where fields are at the top level
                    # Just return the data as is, assuming it's already in the expected format
                    result = issue_data

                logger.debug(f"Extracted issue data structure: {result}")
                return result

            except KeyError as e:
                logger.error(f"Failed to extract issue data - missing field: {str(e)}")
                logger.debug(f"Raw issue data: {issue_data}")
                return None

        except Exception as e:
            logger.error(f"Failed to get JIRA issue {issue_key}: {str(e)}")
            logger.exception("Full traceback:")
            return None

    async def _create_issue(
            self,
            project_key: str,
            summary: str,
            description: Optional[str] = None,
            issue_type: str = "Task",
            parent_key: Optional[str] = None,
            additional_fields: Optional[Dict[str, Any]] = None
    ) -> JiraTicketCreation:
        """
        Create a new JIRA issue using the REST API.
        
        Makes an asynchronous HTTP POST request to create a new issue in JIRA with the 
        specified properties. Handles parent-child relationships for sub-tasks and
        epic links for stories/tasks.
        
        Args:
            project_key (str): The JIRA project key (e.g., "PROJ")
            summary (str): The title/summary of the issue
            description (Optional[str]): The detailed description of the issue
            issue_type (str): The type of issue to create (e.g., "Task", "Story", "Epic")
            parent_key (Optional[str]): For sub-tasks, the parent issue key; for stories/tasks, the epic key
            additional_fields (Optional[Dict[str, Any]]): Any additional fields to set on the issue
                                                         
        Returns:
            JiraTicketCreation: A Pydantic model containing basic information about the created issue
                           
        Raises:
            Exception: If the issue creation fails, with details about the failure
        """
        try:
            # Prepare issue fields
            issue_dict = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": issue_type}
                }
            }

            # Add parent link if provided
            if parent_key:
                if issue_type == "Subtask" or issue_type == "Sub-task":
                    issue_dict["fields"]["parent"] = {"key": parent_key}
                else:
                    # For stories/tasks, use Epic link
                    # Dynamically determine the epic link field
                    epic_link_field = await self._get_epic_link_field()
                    issue_dict["fields"][epic_link_field] = parent_key

            # Add any additional fields
            if additional_fields:
                for field_name, field_value in additional_fields.items():
                    issue_dict["fields"][field_name] = field_value

            # Create the issue
            url = f"{self.api_base_url}/issue"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    headers=self.headers,
                    json=issue_dict,
                    ssl=self.ssl_context
                ) as response:
                    if response.status not in [HTTPStatus.CREATED, HTTPStatus.OK]:
                        error_text = await response.text()
                        logger.error(f"Failed to create issue: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        raise Exception(f"Failed to create issue: {error_text}")

                    response_data = await response.json()
            
            # Construct the return object from what we know
            # The key comes from the response, other fields from our request
            return JiraTicketCreation(
                key=response_data["key"],
                summary=summary,
                # Default status for new issues is typically "To Do" or similar
                status="To Do",  
                issue_type=issue_type
            )

        except Exception as e:
            logger.error(f"Failed to create JIRA issue: {str(e)}")
            logger.error(f"Issue details: project_key={project_key}, summary={summary}, issue_type={issue_type}")
            raise

    def _get_issue_type_id(self, issue_type_name: str) -> str:
        """
        Map issue type names to their IDs.
        
        Different JIRA instances might have different IDs for the same issue types.
        This method provides a mapping based on common defaults.
        
        Args:
            issue_type_name (str): The name of the issue type (e.g., "Story", "Task")
            
        Returns:
            str: The ID of the issue type
        """
        # For Task specifically, use a standard task ID that is not a sub-task
        if issue_type_name == "Task":
            return "10003"  # Standard Task ID
        
        # Common issue type IDs in JIRA Cloud
        issue_type_map = {
            "Bug": "10006",
            "Epic": "10000",
            "Story": "10002",
            "Task": "10003",
            "Sub-task": "10004"
        }
        
        return issue_type_map.get(issue_type_name, "10003")  # Default to Task if not found

    async def _update_issue(
            self,
            issue_key: str,
            fields: Dict[str, Any]
    ) -> bool:
        """
        Update an existing JIRA issue's fields using the REST API.
        
        Makes an asynchronous HTTP PUT request to update the specified fields of an
        existing JIRA issue. Any field that can be modified through the JIRA API
        can be included in the fields dictionary.
        
        Args:
            issue_key (str): The JIRA issue key to update
            fields (Dict[str, Any]): A dictionary of fields to update, where keys are 
                                    field names and values are the new field values
                                    
        Returns:
            bool: True if the update was successful, False otherwise
            
        Note:
            The fields dictionary should match JIRA's expected format. For example:
            {
                "summary": "New summary",
                "description": "New description",
                "assignee": {"name": "username"},
                "labels": ["label1", "label2"]
            }
        """
        try:
            url = f"{self.api_base_url}/issue/{issue_key}"
            update_data = {"fields": fields}
            
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    url, 
                    headers=self.headers,
                    json=update_data,
                    ssl=self.ssl_context
                ) as response:
                    if response.status not in [HTTPStatus.OK, HTTPStatus.NO_CONTENT]:
                        error_text = await response.text()
                        logger.error(f"Failed to update issue {issue_key}: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Failed to update JIRA issue {issue_key}: {str(e)}")
            logger.error(f"Update fields: {fields}")
            return False

    async def _transition_issue(
            self,
            issue_key: str,
            transition_name: str
    ) -> bool:
        """
        Transition a JIRA issue to a new status using the REST API.
        
        This method performs a two-step process:
        1. Fetches the available transitions for the issue
        2. Executes the specified transition if it exists
        
        The transition is identified by name rather than ID, allowing for more intuitive
        usage and compatibility across different JIRA configurations.
        
        Args:
            issue_key (str): The JIRA issue key to transition
            transition_name (str): The name of the transition to perform (case-insensitive)
                                  e.g., "To Do", "In Progress", "Done"
                                  
        Returns:
            bool: True if the transition was successful, False otherwise
            
        Note:
            If the specified transition isn't available for the issue in its current state,
            the method will log the available transitions and return False.
        """
        try:
            # First get available transitions
            url = f"{self.api_base_url}/issue/{issue_key}/transitions"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers,
                    ssl=self.ssl_context
                ) as response:
                    if response.status != HTTPStatus.OK:
                        error_text = await response.text()
                        logger.error(f"Failed to get transitions for {issue_key}: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
                        
                    transitions_data = await response.json()
                    
            # Find the transition ID
            transition_id = None
            for t in transitions_data["transitions"]:
                if t["name"].lower() == transition_name.lower():
                    transition_id = t["id"]
                    break

            if not transition_id:
                logger.error(f"Transition '{transition_name}' not found for issue {issue_key}")
                logger.debug(f"Available transitions: {[t['name'] for t in transitions_data['transitions']]}")
                return False

            # Perform the transition
            transition_url = f"{self.api_base_url}/issue/{issue_key}/transitions"
            transition_data = {
                "transition": {
                    "id": transition_id
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    transition_url, 
                    headers=self.headers,
                    json=transition_data,
                    ssl=self.ssl_context
                ) as response:
                    if response.status not in [HTTPStatus.OK, HTTPStatus.NO_CONTENT]:
                        error_text = await response.text()
                        logger.error(f"Failed to transition issue {issue_key}: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
            
            return True

        except Exception as e:
            logger.error(f"Failed to transition JIRA issue {issue_key}: {str(e)}")
            return False
            
    async def _search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search for JIRA issues using JQL (JIRA Query Language) via the REST API.
        
        Makes an asynchronous HTTP GET request to search for issues matching the provided
        JQL query. Results are paginated according to the max_results parameter.
        
        Args:
            jql (str): The JQL query string to execute
            max_results (int, optional): Maximum number of results to return. Defaults to 50.
            
        Returns:
            List[Dict[str, Any]]: A list of issue data dictionaries matching the query,
                                 or an empty list if no matches or an error occurs
                                 
        Note:
            JQL is a powerful query language similar to SQL. Examples:
            - 'project = PROJECT AND issuetype = Story'
            - 'assignee = currentUser() AND status = "In Progress"'
            - 'created >= -7d AND project = PROJECT'
            
        For complex queries with many results, consider implementing pagination by
        extending this method to support the startAt parameter.
        """
        try:
            url = f"{self.api_base_url}/search"
            params = {
                "jql": jql,
                "maxResults": max_results
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers,
                    params=params,
                    ssl=self.ssl_context
                ) as response:
                    if response.status != HTTPStatus.OK:
                        error_text = await response.text()
                        logger.error(f"Failed to search issues with JQL '{jql}': Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return []
                        
                    search_data = await response.json()
                    
            return search_data["issues"]
            
        except Exception as e:
            logger.error(f"Failed to search JIRA issues with JQL '{jql}': {str(e)}")
            return []

    async def _get_epic_link_field(self) -> str:
        """
        Determine the custom field ID used for epic links in this JIRA instance.
        
        Makes an API call to fetch field metadata and identifies the epic link field
        by its name or description.
        
        Returns:
            str: The custom field ID (e.g., "customfield_10014") for epic links
            
        Raises:
            Exception: If the epic link field cannot be determined
        """
        if self._epic_link_field:
            return self._epic_link_field
            
        try:
            logger.info("Fetching field metadata to identify epic link field")
            url = f"{self.api_base_url}/field"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers,
                    ssl=self.ssl_context
                ) as response:
                    if response.status != HTTPStatus.OK:
                        logger.error(f"Failed to get field metadata: Status {response.status}")
                        logger.error(f"Response: {await response.text()}")
                        raise Exception("Failed to get field metadata from JIRA API")
                        
                    fields = await response.json()
            
            # Look for the epic link field by name or description
            epic_link_field = None
            for field in fields:
                # Check various ways the epic link field might be identified
                name = field.get("name", "").lower()
                if "epic link" in name or "epic" in name and "link" in name:
                    epic_link_field = field["id"]
                    break
                    
                # Check custom field description if available
                description = field.get("description", "").lower()
                if description and ("epic link" in description or ("epic" in description and "link" in description)):
                    epic_link_field = field["id"]
                    break
            
            if not epic_link_field:
                # Fallback to common default values if we couldn't identify it
                logger.warning("Could not identify epic link field, using default customfield_10014")
                epic_link_field = "customfield_10014"
            
            logger.info(f"Identified epic link field: {epic_link_field}")
            self._epic_link_field = epic_link_field
            return epic_link_field
            
        except Exception as e:
            logger.error(f"Failed to determine epic link field: {str(e)}")
            # Fallback to a common default
            logger.warning("Using default epic link field customfield_10014")
            return "customfield_10014"
