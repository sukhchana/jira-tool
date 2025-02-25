from typing import Dict, Any, List, Optional
from http import HTTPStatus

from loguru import logger
import aiohttp

from models.jira_linked_ticket import JiraLinkedTicket
from models.jira_ticket_creation import JiraTicketCreation
from models.jira_ticket_details import JiraTicketDetails

from .base_operation import BaseJiraOperation


class TicketOperations(BaseJiraOperation):
    """
    Operations for managing JIRA tickets (stories, tasks, subtasks).
    
    This class extends BaseJiraOperation to provide specific methods for creating,
    updating, and retrieving different types of JIRA tickets such as user stories,
    tasks, and subtasks. It includes functionality for managing ticket relationships
    and hierarchies.
    
    All methods are implemented as asynchronous coroutines for efficient API interaction.
    """

    async def create_story(
            self,
            project_key: str,
            summary: str,
            description: Optional[str] = None,
            epic_key: Optional[str] = None,
            assignee: Optional[str] = None,
            additional_fields: Optional[Dict[str, Any]] = None
    ) -> JiraTicketCreation:
        """
        Create a new story in JIRA.
        
        Creates a new issue with type "Story" in the specified project. Optionally
        links the story to an epic if an epic key is provided.
        
        Args:
            project_key (str): The JIRA project key where the story will be created
            summary (str): The title/summary of the story
            description (Optional[str]): The detailed description of the story
            epic_key (Optional[str]): If provided, the story will be linked to this epic
            assignee (Optional[str]): If provided, the story will be assigned to this user
            additional_fields (Optional[Dict[str, Any]]): Any additional fields to set on the
                                                        story (e.g., priority, labels, story points)
                                                        
        Returns:
            JiraTicketCreation: A Pydantic model containing basic information about the created story:
                               - key: The issue key
                               - summary: The issue summary
                               - status: The initial status
                               - issue_type: Will be "Story"
                           
        Raises:
            Exception: If the story creation fails, with details about the failure
        """
        try:
            # Prepare additional fields
            fields = additional_fields or {}
            if assignee:
                fields["assignee"] = {"name": assignee}
                
            return await self._create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type="Story",
                parent_key=epic_key,
                additional_fields=fields
            )
        except Exception as e:
            logger.error(f"Failed to create story: {str(e)}")
            raise

    async def create_task(
            self,
            project_key: str,
            summary: str,
            description: str,
            assignee: Optional[str] = None,
            epic_key: Optional[str] = None,
            additional_fields: Optional[Dict[str, Any]] = None
    ) -> JiraTicketCreation:
        """
        Create a technical task in JIRA.
        
        Creates a new issue with type "Task" in the specified project. Tasks typically
        represent technical work items or implementation details. Optionally links
        the task to an epic if an epic key is provided.
        
        Args:
            project_key (str): The JIRA project key where the task will be created
            summary (str): The title/summary of the task
            description (str): The detailed description with technical requirements
            assignee (Optional[str]): If provided, the task will be assigned to this user
            epic_key (Optional[str]): If provided, the task will be linked to this epic
            additional_fields (Optional[Dict[str, Any]]): Any additional fields to set on the
                                                        task (e.g., priority, labels, story points)
                                                        
        Returns:
            JiraTicketCreation: A Pydantic model containing basic information about the created task:
                               - key: The issue key
                               - summary: The issue summary
                               - status: The initial status
                               - issue_type: Will be "Task"
                           
        Raises:
            Exception: If the task creation fails, with details about the failure
        """
        try:
            # Prepare additional fields with assignee if provided
            fields = additional_fields.copy() if additional_fields else {}
            if assignee:
                fields["assignee"] = {"name": assignee}
                
            return await self._create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type="Task",
                parent_key=epic_key,
                additional_fields=fields
            )
        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}")
            raise

    async def create_subtask(
            self,
            project_key: str,
            summary: str,
            description: str,
            parent_key: str,
            assignee: Optional[str] = None,
            additional_fields: Optional[Dict[str, Any]] = None
    ) -> JiraTicketCreation:
        """
        Create a subtask in JIRA.
        
        Creates a new issue with type "Subtask" in the specified project. Subtasks
        are smaller units of work that are part of a larger task or story. The parent_key
        parameter is required as subtasks must be linked to a parent issue.
        
        Args:
            project_key (str): The JIRA project key where the subtask will be created
            summary (str): The title/summary of the subtask
            description (str): The detailed description of the work to be done
            parent_key (str): The key of the parent issue (must be a story or task)
            assignee (Optional[str]): If provided, the subtask will be assigned to this user
            additional_fields (Optional[Dict[str, Any]]): Any additional fields to set on the
                                                        subtask (e.g., priority, labels)
                                                        
        Returns:
            JiraTicketCreation: A Pydantic model containing basic information about the created subtask:
                               - key: The issue key
                               - summary: The issue summary
                               - status: The initial status
                               - issue_type: Will be "Subtask"
                           
        Raises:
            Exception: If the subtask creation fails, with details about the failure
        """
        try:
            # Prepare additional fields with assignee if provided
            fields = additional_fields.copy() if additional_fields else {}
            if assignee:
                fields["assignee"] = {"name": assignee}
                
            return await self._create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type="Subtask",
                parent_key=parent_key,
                additional_fields=fields
            )
        except Exception as e:
            logger.error(f"Failed to create subtask: {str(e)}")
            raise

    async def update_ticket(
            self,
            ticket_key: str,
            fields: Dict[str, Any]
    ) -> bool:
        """
        Update fields of an existing JIRA ticket.
        
        Updates the specified fields of an existing ticket (story, task, or subtask).
        
        Args:
            ticket_key (str): The JIRA issue key to update
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
            return await self._update_issue(ticket_key, fields)
        except Exception as e:
            logger.error(f"Failed to update ticket: {str(e)}")
            return False

    async def update_ticket_status(
            self,
            ticket_key: str,
            status: str
    ) -> bool:
        """
        Update the status of a JIRA ticket by performing a workflow transition.
        
        Transitions the specified ticket to a new status using JIRA's workflow system.
        The status parameter should match one of the available transition names for
        the ticket's current state.
        
        Args:
            ticket_key (str): The JIRA issue key to transition
            status (str): The name of the transition to perform (case-insensitive)
                         e.g., "To Do", "In Progress", "Done"
                         
        Returns:
            bool: True if the status update was successful, False otherwise
            
        Note:
            If the specified status transition isn't available for the ticket in its
            current state, the method will log the available transitions and return False.
        """
        try:
            return await self._transition_issue(ticket_key, status)
        except Exception as e:
            logger.error(f"Failed to update ticket status: {str(e)}")
            return False

    async def get_ticket_details(self, ticket_key: str) -> Optional[JiraTicketDetails]:
        """
        Get details of a JIRA ticket.

        Args:
            ticket_key: The key of the JIRA ticket to get details for.

        Returns:
            JiraTicketDetails object with ticket details, or None if the ticket could not be found.
        """
        logger.debug(f"Fetching ticket details for {ticket_key}")
        try:
            ticket = await self._get_issue(ticket_key)
            if not ticket:
                logger.warning(f"Ticket {ticket_key} not found")
                return None

            # Extract fields from the ticket data
            fields = ticket.get("fields", {})
            
            # Extract issue type
            issue_type_obj = fields.get("issuetype", {})
            issue_type = issue_type_obj.get("name") if issue_type_obj else None
            logger.debug(f"Ticket {ticket_key} is of type {issue_type}")
            
            # Extract reporter and priority names from their objects
            reporter_obj = fields.get("reporter", {})
            reporter = reporter_obj.get("displayName") if reporter_obj else None
            
            priority_obj = fields.get("priority", {})
            priority = priority_obj.get("name") if priority_obj else None
            
            # Extract status
            status_obj = fields.get("status", {})
            status = status_obj.get("name") if status_obj else None
            
            # Extract component names
            components = [c.get("name") for c in fields.get("components", []) if c.get("name")]
            
            # Get the epic link field
            epic_link_field = await self._get_epic_link_field()
            
            # Create and return the ticket details
            ticket_details = JiraTicketDetails(
                key=ticket.get("key"),
                summary=fields.get("summary"),
                description=fields.get("description"),
                status=status,
                issue_type=issue_type,
                project_key=ticket_key.split("-")[0],
                created=fields.get("created"),
                updated=fields.get("updated"),
                assignee=fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                reporter=reporter,
                priority=priority,
                labels=fields.get("labels", []),
                components=components,
                parent_key=fields.get("parent", {}).get("key") if fields.get("parent") else None,
                epic_key=fields.get(epic_link_field),  # Use the dynamically determined epic link field
                story_points=fields.get("customfield_10016"),  # Assuming this is the story points field
                custom_fields={
                    k: v for k, v in fields.items()
                    if k.startswith("customfield_") and v is not None
                }
            )
            return ticket_details
        except Exception as e:
            logger.error(f"Failed to get ticket details for {ticket_key}: {e}")
            logger.error(f"Full traceback:", exc_info=True)
            return None

    async def get_linked_tickets(
            self,
            ticket_key: str,
            link_type: Optional[str] = None
    ) -> List[JiraLinkedTicket]:
        """
        Get tickets linked to the specified JIRA ticket.
        
        Retrieves information about tickets that are linked to the specified ticket,
        optionally filtered by link type. These are links created using JIRA's issue
        linking feature, not parent-child or epic relationships.
        
        Args:
            ticket_key (str): The JIRA issue key to find links for
            link_type (Optional[str]): If provided, only return links of this type
                                      (e.g., "blocks", "is blocked by", "relates to")
                                      
        Returns:
            List[JiraLinkedTicket]: A list of Pydantic models, each containing information
                                    about a linked ticket. Returns an empty list if no
                                    linked tickets are found or an error occurs.
                                 
        Each linked ticket model includes:
            - key: The linked issue key
            - link_type: The type of link (e.g., "blocks", "is blocked by")
            - summary: The linked issue summary
            - status: The linked issue status
            - issue_type: The linked issue type
        """
        try:
            # Get issue details with the links field
            url = f"{self.api_base_url}/issue/{ticket_key}?fields=issuelinks"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers,
                    ssl=self.ssl_context
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get issue links: Status {response.status}")
                        return []
                        
                    issue_data = await response.json()
            
            linked_tickets = []
            
            if "fields" not in issue_data or "issuelinks" not in issue_data["fields"]:
                return []
                
            # Process each link
            for link in issue_data["fields"]["issuelinks"]:
                # Determine link type and linked issue
                if "outwardIssue" in link:
                    linked_issue = link["outwardIssue"]
                    current_link_type = link["type"]["outward"]
                elif "inwardIssue" in link:
                    linked_issue = link["inwardIssue"]
                    current_link_type = link["type"]["inward"]
                else:
                    continue
                    
                # Filter by link type if specified
                if link_type and current_link_type.lower() != link_type.lower():
                    continue
                    
                # Get the linked issue details
                linked_issue_key = linked_issue["key"]
                linked_issue_details = await self._get_issue(linked_issue_key)
                
                if not linked_issue_details:
                    logger.warning(f"Could not retrieve details for linked issue {linked_issue_key}")
                    continue
                    
                # Add the linked ticket to the result
                linked_ticket = JiraLinkedTicket(
                    key=linked_issue_key,
                    link_type=current_link_type,
                    summary=linked_issue_details["summary"],
                    status=linked_issue_details["status"]["name"],
                    issue_type=linked_issue_details["issuetype"]["name"]
                )
                    
                linked_tickets.append(linked_ticket)
                
            return linked_tickets
            
        except Exception as e:
            logger.error(f"Failed to get linked tickets for {ticket_key}: {str(e)}")
            return []

    async def add_comment(
            self,
            ticket_key: str,
            comment_text: str
    ) -> bool:
        """
        Add a comment to a JIRA ticket.
        
        Posts a new comment to the specified JIRA issue using the REST API.
        
        Args:
            ticket_key (str): The JIRA issue key to comment on
            comment_text (str): The text content of the comment
            
        Returns:
            bool: True if the comment was added successfully, False otherwise
        """
        try:
            url = f"{self.api_base_url}/issue/{ticket_key}/comment"
            comment_data = {
                "body": comment_text
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=comment_data,
                    ssl=self.ssl_context
                ) as response:
                    if response.status not in [HTTPStatus.CREATED, HTTPStatus.OK]:
                        error_text = await response.text()
                        logger.error(f"Failed to add comment to {ticket_key}: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
            
            logger.info(f"Successfully added comment to {ticket_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add comment to JIRA issue {ticket_key}: {str(e)}")
            return False
