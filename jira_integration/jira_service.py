import aiohttp
import base64
import os
import ssl
from typing import Dict, Any, List, Optional

from fastapi import HTTPException
from loguru import logger

from jira_integration.operations import EpicOperations, TicketOperations
from models.jira_epic_progress import JiraEpicProgress
from models.jira_linked_ticket import JiraLinkedTicket
from models.jira_project import JiraProject
from models.jira_ticket_creation import JiraTicketCreation
from models.jira_ticket_details import JiraTicketDetails
from models.jira_epic_details import JiraEpicDetails


class JiraService:
    """
    Service for interacting with JIRA REST API.
    
    This service provides a high-level interface for JIRA operations, including
    ticket management, project retrieval, and ticket status updates. It uses
    specialized operation classes (EpicOperations, TicketOperations) internally
    to handle different types of JIRA issues.
    
    The service abstracts away the details of the REST API implementation and
    provides a consistent interface for the application to interact with JIRA.
    """

    def __init__(self):
        """
        Initialize the JIRA service with operation classes and API configuration.
        
        Creates instances of specialized operation classes and sets up common
        configuration for direct API access, including authentication headers
        and SSL context.
        """
        self.epic_ops = EpicOperations()
        self.ticket_ops = TicketOperations()

        self.jira_url = os.getenv('JIRA_SERVER')
        self.base_url = f"{self.jira_url}/rest/api/2"

        self.set_headers_basic()

        # Create SSL context that doesn't verify
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def set_headers_basic(self):
        """
        Set up HTTP headers with Basic Authentication for JIRA API calls.
        
        Retrieves credentials from environment variables and creates the
        Authorization header using Base64 encoding.
        
        Raises:
            ValueError: If required environment variables are missing
        """
        # Get credentials from environment
        email = os.getenv('JIRA_EMAIL')
        api_token = os.getenv('JIRA_API_TOKEN')

        if not email or not api_token:
            raise ValueError("JIRA_EMAIL and JIRA_API_TOKEN must be set in environment")

        # Create base64 encoded auth string
        auth_string = f"{email}:{api_token}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()

        self.headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def get_ticket(self, ticket_key: str) -> Optional[JiraTicketDetails]:
        """
        Retrieve a JIRA ticket by its key and convert it to a JiraTicketDetails model.
        
        Determines if the ticket is an epic or regular ticket based on its key pattern,
        then delegates to the appropriate operations class to fetch details. The raw
        data is then converted to a standardized JiraTicketDetails model.
        
        Args:
            ticket_key (str): The JIRA issue key to retrieve
            
        Returns:
            Optional[JiraTicketDetails]: A Pydantic model containing the ticket details,
                                        or None if the ticket cannot be retrieved
                                        
        Note:
            The method assumes epics have keys with a pattern where the numeric
            part starts with 'E' (e.g., "PROJECT-E123"). This pattern might need
            adjustment for different JIRA configurations.
        """
        try:
            logger.info(f"Attempting to fetch ticket: {ticket_key}")

            # Check if it's an epic based on key format (this is just an example, adjust to your JIRA setup)
            is_epic = ticket_key.split("-")[1].startswith("E")
            logger.debug(f"Ticket {ticket_key} is_epic: {is_epic}")

            if is_epic:
                logger.info(f"Fetching epic details for {ticket_key}")
                epic_details = await self.epic_ops.get_epic_details(ticket_key)
                if epic_details is None:
                    logger.error(f"Epic {ticket_key} details returned None")
                    return None
                    
                # Convert JiraEpicDetails to JiraTicketDetails
                ticket_details = JiraTicketDetails(
                    key=epic_details.key,
                    summary=epic_details.summary,
                    description=epic_details.description,
                    issue_type=epic_details.status,
                    status=epic_details.status,
                    project_key=epic_details.project_key,
                    created=epic_details.created,
                    updated=epic_details.updated,
                    assignee=epic_details.assignee,
                    reporter=epic_details.reporter,
                    priority=epic_details.priority,
                    labels=epic_details.labels,
                    components=epic_details.components,
                    custom_fields=epic_details.custom_fields
                )
                
                return ticket_details
            else:
                logger.info(f"Fetching regular ticket details for {ticket_key}")
                return await self.ticket_ops.get_ticket_details(ticket_key)

        except Exception as e:
            logger.error(f"Error getting ticket {ticket_key}: {str(e)}")
            logger.exception("Full traceback:")
            return None

    async def create_ticket(self, ticket_data: Dict[str, Any]) -> JiraTicketCreation:
        """
        Create a new JIRA ticket based on the specified type.
        
        Delegates to the appropriate operations class based on the ticket type
        (epic, story, task, sub-task). Validates required fields and handles
        parent/epic relationships for hierarchical tickets.
        
        Args:
            ticket_data (Dict[str, Any]): A dictionary containing ticket details:
                - issue_type: The type of ticket to create (epic, story, task, sub-task)
                - project_key: The JIRA project key
                - summary: The ticket summary/title
                - description: The ticket description
                - parent_key: (Optional) For sub-tasks, the parent issue key;
                              for stories/tasks, the epic key
                - Additional fields as needed
                
        Returns:
            JiraTicketCreation: A Pydantic model with information about the created ticket
            
        Raises:
            ValueError: If required fields are missing or the issue type is unsupported
            Exception: If ticket creation fails for any reason
        """
        try:
            issue_type = ticket_data.get("issue_type", "").lower()
            project_key = ticket_data.get("project_key")
            summary = ticket_data.get("summary")
            description = ticket_data.get("description")
            parent_key = ticket_data.get("parent_key")

            if not all([project_key, summary, description]):
                raise ValueError("Missing required ticket fields")

            # Prepare additional fields
            additional_fields = {
                k: v for k, v in ticket_data.items()
                if k not in ["project_key", "summary", "description", "issue_type", "parent_key"]
            }

            if issue_type == "epic":
                return await self.epic_ops.create_epic(
                    project_key=project_key,
                    summary=summary,
                    description=description,
                    additional_fields=additional_fields
                )
            elif issue_type == "story":
                return await self.ticket_ops.create_story(
                    project_key=project_key,
                    summary=summary,
                    description=description,
                    epic_key=parent_key,
                    additional_fields=additional_fields
                )
            elif issue_type == "task":
                return await self.ticket_ops.create_task(
                    project_key=project_key,
                    summary=summary,
                    description=description,
                    epic_key=parent_key,
                    additional_fields=additional_fields
                )
            elif issue_type == "sub-task":
                if not parent_key:
                    raise ValueError("Parent key is required for sub-tasks")
                    
                return await self.ticket_ops.create_subtask(
                    project_key=project_key,
                    summary=summary,
                    description=description,
                    parent_key=parent_key,
                    additional_fields=additional_fields
                )
            else:
                raise ValueError(f"Unsupported issue type: {issue_type}")

        except Exception as e:
            logger.error(f"Failed to create ticket: {str(e)}")
            raise

    async def update_ticket(
            self,
            ticket_key: str,
            fields: Dict[str, Any]
    ) -> bool:
        """
        Update the fields of an existing JIRA ticket.
        
        Determines if the ticket is an epic or regular ticket based on its key pattern,
        then delegates to the appropriate operations class to update the fields.
        
        Args:
            ticket_key (str): The JIRA issue key to update
            fields (Dict[str, Any]): A dictionary of fields to update
            
        Returns:
            bool: True if the update was successful, False otherwise
            
        Note:
            For epics, only status updates are supported through this method.
            For other ticket types, any field can be updated.
        """
        try:
            if ticket_key.split("-")[1].startswith("E"):
                return await self.epic_ops.update_epic_status(ticket_key, fields.get("status"))
            else:
                return await self.ticket_ops.update_ticket(ticket_key, fields)
        except Exception as e:
            logger.error(f"Failed to update ticket: {str(e)}")
            return False

    async def update_ticket_status(
            self,
            ticket_key: str,
            status: str
    ) -> bool:
        """
        Update the status of a JIRA ticket.
        
        Delegates to the appropriate operations class based on whether the ticket
        is an epic or regular issue. The status change is performed using JIRA's
        workflow transitions.
        
        Args:
            ticket_key (str): The JIRA issue key to update
            status (str): The target status name (e.g., "In Progress", "Done")
            
        Returns:
            bool: True if the status was updated successfully, False otherwise
        """
        try:
            # Check if this is an epic (key pattern with E)
            if self._is_epic_key(ticket_key):
                return await self.epic_ops.update_epic_status(ticket_key, status)
            else:
                return await self.ticket_ops.update_ticket_status(ticket_key, status)
        except Exception as e:
            logger.error(f"Failed to update ticket status: {str(e)}")
            return False

    async def add_comment(
            self,
            ticket_key: str,
            comment_text: str
    ) -> bool:
        """
        Add a comment to a JIRA ticket.
        
        Delegates to the ticket operations class to add the comment.
        
        Args:
            ticket_key (str): The JIRA issue key to comment on
            comment_text (str): The text content of the comment
            
        Returns:
            bool: True if the comment was added successfully, False otherwise
        """
        try:
            return await self.ticket_ops.add_comment(ticket_key, comment_text)
        except Exception as e:
            logger.error(f"Failed to add comment: {str(e)}")
            return False

    async def get_epic_progress(self, epic_key: str) -> JiraEpicProgress:
        """
        Get progress statistics for a JIRA epic.
        
        Retrieves completion metrics for an epic, including counts of total and
        completed issues, and calculation of completion percentage.
        
        Args:
            epic_key (str): The JIRA issue key for the epic
            
        Returns:
            JiraEpicProgress: A Pydantic model containing progress metrics, including:
                             - total_issues: Total number of issues in the epic
                             - completed_issues: Number of issues in a "done" state
                             - completion_percentage: Percentage of completed issues
                             - counts for different issue types
                           
        Raises:
            Exception: If retrieval or calculation of progress metrics fails
        """
        return await self.epic_ops.get_epic_progress(epic_key)

    async def get_linked_tickets(self, issue_key: str) -> List[JiraLinkedTicket]:
        return await self.ticket_ops.get_linked_tickets(issue_key)

    async def get_projects(self) -> List[JiraProject]:
        """
        Get a list of available JIRA projects.
        
        Makes a direct REST API call to retrieve all projects the authenticated user
        has access to. The projects are converted to JiraProject models.
        
        Returns:
            List[JiraProject]: A list of projects, each as a JiraProject model
            
        Raises:
            HTTPException: If the API call fails
            Exception: For any other errors
        """
        try:
            url = f"{self.base_url}/project"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                        url,
                        headers=self.headers,
                        ssl=self.ssl_context
                ) as response:
                    if response.status == 200:
                        projects = await response.json()
                        return [
                            JiraProject(
                                key=project.get("key"),
                                name=project.get("name"),
                                id=project.get("id")
                            )
                            for project in projects
                        ]
                    else:
                        error_msg = (
                            f"Failed to fetch JIRA projects:\n"
                            f"Status: {response.status}\n"
                            f"Response: {await response.text()}"
                        )
                        raise HTTPException(status_code=response.status, detail=error_msg)

        except Exception as e:
            logger.error(f"Failed to fetch projects: {str(e)}")
            raise

    async def create_story(
            self,
            project_key: str,
            summary: str,
            description: str,
            assignee: Optional[str] = None
    ) -> JiraTicketCreation:
        """
        Create a user story in JIRA.
        
        Delegates to the ticket_ops class to create a story and returns a standardized
        response model.
        
        Args:
            project_key (str): The JIRA project key
            summary (str): The story title/summary
            description (str): The story description
            assignee (Optional[str]): Email of the user to assign the story to
            
        Returns:
            JiraTicketCreation: Details of the created story
        """
        additional_fields = {}
        if assignee:
            additional_fields["assignee"] = {"name": assignee}
            
        return await self.ticket_ops.create_story(
            project_key=project_key,
            summary=summary,
            description=description,
            additional_fields=additional_fields
        )
        
    async def create_epic(
            self,
            project_key: str,
            summary: str,
            description: str,
            assignee: Optional[str] = None
    ) -> JiraTicketCreation:
        """
        Create an epic in JIRA.
        
        Delegates to the epic_ops class to create an epic and returns a standardized
        response model.
        
        Args:
            project_key (str): The JIRA project key
            summary (str): The epic title/summary
            description (str): The epic description
            assignee (Optional[str]): Email of the user to assign the epic to
            
        Returns:
            JiraTicketCreation: Details of the created epic
        """
        additional_fields = {}
        if assignee:
            additional_fields["assignee"] = {"name": assignee}
            
        return await self.epic_ops.create_epic(
            project_key=project_key,
            summary=summary,
            description=description,
            additional_fields=additional_fields
        )

    def _is_epic_key(self, ticket_key: str) -> bool:
        """
        Check if a ticket key is for an epic.
        
        Args:
            ticket_key (str): The JIRA issue key to check
            
        Returns:
            bool: True if the ticket is for an epic, False otherwise
        """
        return ticket_key.split("-")[1].startswith("E")

    async def create_task(self, project_key: str, summary: str, description: str, assignee: Optional[str] = None) -> JiraTicketCreation:
        """
        Create a task in JIRA.

        :param project_key: The JIRA project key.
        :param summary: The summary of the task.
        :param description: The description of the task.
        :param assignee: The assignee of the task.
        :return: JiraTicketCreation object with details of the created task.
        """
        additional_fields = {'assignee': {'name': assignee}} if assignee else {}
        return await self.ticket_ops.create_task(
            project_key=project_key,
            summary=summary,
            description=description,
            additional_fields=additional_fields
        )

    async def create_subtask(self, parent_key: str, project_key: str, summary: str, description: str, assignee: Optional[str] = None) -> JiraTicketCreation:
        """
        Create a subtask in JIRA.

        :param parent_key: The parent issue key.
        :param project_key: The JIRA project key.
        :param summary: The summary of the subtask.
        :param description: The description of the subtask.
        :param assignee: The assignee of the subtask.
        :return: JiraTicketCreation object with details of the created subtask.
        """
        additional_fields = {'assignee': {'name': assignee}} if assignee else {}
        return await self.ticket_ops.create_subtask(
            parent_key=parent_key,
            project_key=project_key,
            summary=summary,
            description=description,
            additional_fields=additional_fields
        )

    async def get_epic_details(self, epic_key: str) -> JiraEpicDetails:
        """
        Get the details of an epic in JIRA.

        :param epic_key: The JIRA issue key for the epic.
        :return: JiraEpicDetails object with details of the epic.
        """
        return await self.epic_ops.get_epic_details(epic_key)

    async def assign_to_epic(self, epic_key: str, issue_key: str) -> bool:
        """
        Assign an issue to an epic in JIRA.

        :param epic_key: The JIRA issue key for the epic.
        :param issue_key: The JIRA issue key for the issue to assign.
        :return: True if the assignment was successful, False otherwise.
        """
        return await self.epic_ops.assign_issue_to_epic(epic_key, issue_key)

    async def remove_from_epic(self, issue_key: str) -> bool:
        """
        Remove an issue from an epic in JIRA.

        :param issue_key: The JIRA issue key for the issue to remove.
        :return: True if the removal was successful, False otherwise.
        """
        return await self.epic_ops.remove_issue_from_epic(issue_key)

    async def update_epic(self, epic_key: str, update_data: Dict[str, Any]) -> bool:
        """
        Update the details of an epic in JIRA.

        :param epic_key: The JIRA issue key for the epic.
        :param update_data: A dictionary containing the fields to update.
        :return: True if the update was successful, False otherwise.
        """
        return await self.epic_ops.update_epic_details(
            epic_key=epic_key,
            **update_data
        )
