from typing import Dict, Any, Optional, List

from loguru import logger
import aiohttp
from http import HTTPStatus

from models.jira_epic_details import JiraEpicDetails 
from models.jira_epic_progress import JiraEpicProgress
from models.jira_ticket_creation import JiraTicketCreation
from models.jira_ticket_details import JiraTicketDetails

from .base_operation import BaseJiraOperation


class EpicOperations(BaseJiraOperation):
    """
    Operations for managing JIRA epics.
    
    This class extends BaseJiraOperation to provide specific methods for creating,
    updating, and retrieving JIRA epics. Epics are large work items that can contain
    stories, tasks, and other issue types, and are often used to organize work around
    features or initiatives.
    
    The class includes methods for creating epics, retrieving epic details including
    linked issues, updating epic status, and calculating progress metrics.
    
    All methods are implemented as asynchronous coroutines for efficient API interaction.
    """

    def __init__(self):
        super().__init__()
        self.logger = logger

    async def get_epic_details(self, epic_key: str) -> Optional[JiraEpicDetails]:
        """
        Get detailed information about a JIRA epic.
        
        Retrieves comprehensive information about an epic, including its fields and
        all issues linked to it (stories, tasks, subtasks). The method verifies that
        the issue is actually an epic before proceeding with data collection.
        
        Args:
            epic_key (str): The JIRA issue key for the epic (e.g., "PROJECT-123")
            
        Returns:
            Optional[JiraEpicDetails]: A Pydantic model containing the epic details in a standardized
                                      format, or None if the epic cannot be retrieved or processed
                                     
        Raises:
            ValueError: If the issue exists but is not an epic
            
        The returned model includes:
            - All fields from the base issue data
            - stories: A list of story issues linked to this epic
            - tasks: A list of task issues linked to this epic
            - subtasks: A list of subtask issues linked to this epic
            - total_issues: The total count of all linked issues
        """
        try:
            logger.info(f"Fetching epic details from JIRA for {epic_key}")

            # Fetch the epic issue
            epic = await self._get_issue(epic_key)

            if not epic:
                logger.error(f"Could not find issue {epic_key} in JIRA")
                return None

            if not isinstance(epic, dict):
                logger.error(f"Unexpected epic data type: {type(epic)}")
                return None

            # Check issue type using the structure - issue type is in the fields dictionary
            issue_type = epic.get("fields", {}).get("issuetype", {}).get("name")
            logger.debug(f"Issue type for {epic_key}: {issue_type}")

            if not issue_type or issue_type != "Epic":
                logger.error(f"Issue {epic_key} is not an epic (type: {issue_type})")
                raise ValueError(f"Issue {epic_key} is not an epic")

            # Get the epic link field
            epic_link_field = await self._get_epic_link_field()

            # Get all issues linked to this epic using JQL
            logger.info(f"Fetching linked issues for epic {epic_key}")
            jql = f'{epic_link_field} = {epic_key} ORDER BY created DESC'
            logger.debug(f"JQL query: {jql}")
            
            linked_issues = await self._search_issues(jql)
            logger.info(f"Found {len(linked_issues)} issues linked to epic {epic_key}")
            
            # Group issues by type
            stories = []
            tasks = []
            subtasks = []
            
            for issue in linked_issues:
                issue_data = {
                    "key": issue["key"],
                    "summary": issue["fields"]["summary"],
                    "description": issue["fields"].get("description", ""),
                    "issuetype": {
                        "name": issue["fields"]["issuetype"]["name"]
                    },
                    "status": {
                        "name": issue["fields"]["status"]["name"]
                    },
                    "project": {
                        "key": issue["fields"]["project"]["key"]
                    },
                    "created": issue["fields"]["created"],
                    "updated": issue["fields"]["updated"],
                }
                
                # Convert to JiraTicketDetails
                ticket_details = JiraTicketDetails(
                    key=issue_data["key"],
                    summary=issue_data["summary"],
                    description=issue_data.get("description", ""),
                    issue_type=issue_data["issuetype"]["name"],
                    status=issue_data["status"]["name"],
                    project_key=issue_data["project"]["key"],
                    created=issue_data["created"],
                    updated=issue_data["updated"]
                )
                
                if issue["fields"]["issuetype"]["name"] == "Story":
                    stories.append(ticket_details)
                elif issue["fields"]["issuetype"]["name"] == "Task":
                    tasks.append(ticket_details)
                elif issue["fields"]["issuetype"]["name"] == "Sub-task":
                    subtasks.append(ticket_details)
            
            # Create the epic details model
            epic_details = JiraEpicDetails(
                key=epic["key"],
                summary=epic["fields"]["summary"],
                description=epic["fields"].get("description", ""),
                status=epic["fields"]["status"]["name"],
                project_key=epic["fields"]["project"]["key"],
                created=epic["fields"]["created"],
                updated=epic["fields"]["updated"],
                assignee=epic["fields"].get("assignee", {}).get("displayName") if epic["fields"].get("assignee") else None,
                reporter=epic["fields"].get("reporter", {}).get("displayName") if epic["fields"].get("reporter") else None,
                priority=epic["fields"].get("priority", {}).get("name") if epic["fields"].get("priority") else None,
                labels=epic["fields"].get("labels", []),
                components=[c["name"] for c in epic["fields"].get("components", [])],
                
                # Epic-specific fields
                stories=stories,
                tasks=tasks,
                subtasks=subtasks,
                total_issues=len(stories) + len(tasks) + len(subtasks),
                
                # Custom fields
                custom_fields={
                    k: v for k, v in epic.items()
                    if k.startswith("customfield_") and v is not None
                }
            )
            
            return epic_details

        except ValueError as e:
            # Re-raise ValueError for issue type mismatch
            raise
        except Exception as e:
            logger.error(f"Failed to get epic details for {epic_key}: {str(e)}")
            logger.exception("Full traceback:")
            return None

    async def create_epic(
            self,
            project_key: str,
            summary: str,
            description: str,
            assignee: Optional[str] = None,
            additional_fields: Optional[Dict[str, Any]] = None
    ) -> JiraTicketCreation:
        """
        Create a new epic in JIRA.
        
        Creates a new issue with type "Epic" in the specified project. Epics are 
        used to organize and group related stories and tasks.
        
        Args:
            project_key (str): The JIRA project key where the epic will be created
            summary (str): The title/summary of the epic
            description (str): The detailed description of the epic's scope and goals
            assignee (Optional[str]): The assignee for the epic
            additional_fields (Optional[Dict[str, Any]]): Any additional fields to set on the
                                                        epic (e.g., priority, labels, due date)
                                                        
        Returns:
            JiraTicketCreation: A Pydantic model containing basic information about the created epic:
                               - key: The issue key
                               - summary: The issue summary
                               - status: The initial status
                               - issue_type: Will be "Epic"
                           
        Raises:
            Exception: If the epic creation fails, with details about the failure
            
        Note:
            In many JIRA configurations, epics require a "Epic Name" custom field.
            If needed, include this in the additional_fields parameter.
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
                issue_type="Epic",
                additional_fields=fields
            )
        except Exception as e:
            logger.error(f"Failed to create epic: {str(e)}")
            raise

    async def update_epic_status(self, epic_key: str, status: str) -> bool:
        """
        Update the status of a JIRA epic by performing a workflow transition.
        
        Transitions the specified epic to a new status using JIRA's workflow system.
        The status parameter should match one of the available transition names for
        the epic's current state.
        
        Args:
            epic_key (str): The JIRA issue key for the epic to transition
            status (str): The name of the transition to perform (case-insensitive)
                         e.g., "To Do", "In Progress", "Done"
                         
        Returns:
            bool: True if the status update was successful, False otherwise
            
        Note:
            If the specified status transition isn't available for the epic in its
            current state, the method will log the available transitions and return False.
        """
        try:
            return await self._transition_issue(epic_key, status)
        except Exception as e:
            logger.error(f"Failed to update epic status: {str(e)}")
            return False

    async def get_epic_progress(self, epic_key: str) -> JiraEpicProgress:
        """
        Calculate and return progress statistics for a JIRA epic.
        
        Analyzes all issues linked to the epic and calculates completion metrics
        based on their statuses. This provides a quantitative view of the epic's
        overall progress.
        
        Args:
            epic_key (str): The JIRA issue key for the epic
            
        Returns:
            JiraEpicProgress: A Pydantic model containing progress metrics:
                             - total_issues: Total number of issues linked to the epic
                             - completed_issues: Number of issues in a "done" state
                             - done_issues: Number of issues in a "done" state
                             - completion_percentage: Percentage of completed issues
                             - stories_count: Number of story issues
                             - tasks_count: Number of task issues
                             - subtasks_count: Number of subtask issues
                           
        Raises:
            ValueError: If the epic cannot be found
            Exception: If there's an error calculating progress metrics
            
        Note:
            Issues are considered "completed" if their status name (lowercase) matches
            one of: "done", "completed", "closed". This may need adjustment for
            different JIRA workflow configurations.
        """
        try:
            epic = await self.get_epic_details(epic_key)
            if not epic:
                raise ValueError(f"Epic {epic_key} not found")

            # Calculate statistics
            total_issues = epic.total_issues
            completed_issues = sum(
                1 for issues in [epic.stories, epic.tasks, epic.subtasks]
                for issue in issues
                if issue.status.lower() in ["done", "completed", "closed"]
            )

            return JiraEpicProgress(
                total_issues=total_issues,
                completed_issues=completed_issues,
                done_issues=completed_issues,
                completion_percentage=(completed_issues / total_issues * 100) if total_issues > 0 else 0,
                stories_count=len(epic.stories),
                tasks_count=len(epic.tasks),
                subtasks_count=len(epic.subtasks)
            )

        except Exception as e:
            logger.error(f"Failed to get epic progress for {epic_key}: {str(e)}")
            raise

    async def assign_issue_to_epic(self, epic_key: str, issue_key: str) -> bool:
        """
        Assign an issue to an epic.
        Args:
            epic_key (str): The key of the epic.
            issue_key (str): The key of the issue to assign to the epic.
        Returns:
            bool: True if the assignment was successful, False otherwise.
        """
        try:
            logger.info(f"Assigning issue {issue_key} to epic {epic_key}")
            
            # Try multiple approaches in sequence
            
            # 1. First approach: Try direct field update with Epic Link field
            if await self._try_direct_epic_link_update(epic_key, issue_key):
                return True
                
            # 2. Second approach: Try issue link endpoint
            if await self._try_issue_link_method(epic_key, issue_key):
                return True
                
            # 3. Third approach: Try transitions
            if await self._try_transition_method(epic_key, issue_key):
                return True
                
            # 4. Fourth approach: Try REST API v3
            if await self._try_v3_api_method(epic_key, issue_key):
                return True
                
            logger.error(f"All attempts to assign issue {issue_key} to epic {epic_key} failed")
            return False
            
        except Exception as e:
            logger.error(f"Exception while assigning issue to epic: {str(e)}")
            return False
            
    async def _try_direct_epic_link_update(self, epic_key, issue_key):
        """Try the direct field update approach to assign an issue to an epic"""
        try:
            # First, get the field information to determine the epic link field
            fields_endpoint = f"{self.api_base_url}/field"
            async with aiohttp.ClientSession() as session:
                async with session.get(fields_endpoint, headers=self.headers, ssl=self.ssl_context) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get field information: Status {response.status}")
                        return False
                    
                    fields = await response.json()
                    
            # Find the epic link field - it could be 'customfield_10014' or another custom field
            epic_link_field = None
            for field in fields:
                if field.get('name') == 'Epic Link':
                    epic_link_field = field.get('id')
                    break
            
            if not epic_link_field:
                logger.error("Could not find Epic Link field in JIRA instance")
                return False
                
            logger.info(f"Found Epic Link field: {epic_link_field}")
            
            # Prepare update data
            update_data = {
                "fields": {
                    epic_link_field: epic_key
                }
            }
            
            # Send the update request
            endpoint = f"{self.api_base_url}/issue/{issue_key}"
            async with aiohttp.ClientSession() as session:
                async with session.put(endpoint, headers=self.headers, json=update_data, ssl=self.ssl_context) as response:
                    if response.status == 204 or response.status == 200:
                        logger.info(f"Successfully assigned issue {issue_key} to epic {epic_key} via direct update")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to assign issue to epic via direct update: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Exception during direct epic link update: {str(e)}")
            return False
            
    async def _try_issue_link_method(self, epic_key, issue_key):
        """Try the issue link endpoint approach to link an issue to an epic"""
        try:
            logger.info(f"Trying issue link method to assign issue {issue_key} to epic {epic_key}")
            
            # Get the available link types to find the correct one for epics
            link_types_endpoint = f"{self.api_base_url}/issueLinkType"
            async with aiohttp.ClientSession() as session:
                async with session.get(link_types_endpoint, headers=self.headers, ssl=self.ssl_context) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get link types: Status {response.status}")
                        return False
                    
                    link_types_data = await response.json()
                    link_types = link_types_data.get("issueLinkTypes", [])
                    
                    # Find a suitable link type for epics
                    epic_link_type = None
                    for link_type in link_types:
                        name = link_type.get("name", "").lower()
                        if "epic" in name or "parent" in name or "relates" in name:
                            epic_link_type = link_type.get("name")
                            logger.info(f"Found suitable link type: {epic_link_type}")
                            break
                    
                    if not epic_link_type:
                        # If no specific epic link type found, use "Relates"
                        epic_link_type = "Relates"
            
            # Create a link between the issue and epic
            link_data = {
                "type": {
                    "name": epic_link_type
                },
                "inwardIssue": {
                    "key": epic_key
                },
                "outwardIssue": {
                    "key": issue_key
                }
            }
            
            endpoint = f"{self.api_base_url}/issueLink"
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=self.headers, json=link_data, ssl=self.ssl_context) as response:
                    if response.status == 201 or response.status == 200:
                        logger.info(f"Successfully linked issue {issue_key} to epic {epic_key} using link method")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to link issue to epic using link method: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Exception during issue link method: {str(e)}")
            return False
        
    async def _try_transition_method(self, epic_key, issue_key):
        """Try using transitions to update the epic link field"""
        try:
            logger.info(f"Trying transition method to assign issue {issue_key} to epic {epic_key}")
            
            # First, get available transitions for the issue
            transitions_endpoint = f"{self.api_base_url}/issue/{issue_key}/transitions"
            async with aiohttp.ClientSession() as session:
                async with session.get(transitions_endpoint, headers=self.headers, ssl=self.ssl_context) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get transitions: Status {response.status}")
                        return False
                    
                    transitions_data = await response.json()
                    transitions = transitions_data.get("transitions", [])
                    
                    if not transitions:
                        logger.error(f"No transitions available for issue {issue_key}")
                        return False
                    
                    # Use the first transition (usually "In Progress")
                    transition_id = transitions[0].get("id")
            
            # Get the epic link field
            fields_endpoint = f"{self.api_base_url}/field"
            epic_link_field = None
            async with aiohttp.ClientSession() as session:
                async with session.get(fields_endpoint, headers=self.headers, ssl=self.ssl_context) as response:
                    if response.status == 200:
                        fields = await response.json()
                        for field in fields:
                            if field.get('name') == 'Epic Link':
                                epic_link_field = field.get('id')
                                break
            
            if not epic_link_field:
                logger.error("Could not find Epic Link field")
                return False
            
            # Prepare transition data
            transition_data = {
                "transition": {
                    "id": transition_id
                },
                "fields": {
                    epic_link_field: epic_key
                }
            }
            
            # Send the transition request
            endpoint = f"{self.api_base_url}/issue/{issue_key}/transitions"
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=self.headers, json=transition_data, ssl=self.ssl_context) as response:
                    if response.status == 204 or response.status == 200:
                        logger.info(f"Successfully assigned issue {issue_key} to epic {epic_key} via transition")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to assign issue to epic via transition: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Exception during transition method: {str(e)}")
            return False
            
    async def _try_v3_api_method(self, epic_key, issue_key):
        """Try using the REST API v3 to update the epic link field"""
        try:
            logger.info(f"Trying REST API v3 method to assign issue {issue_key} to epic {epic_key}")
            
            # Get base API URL without "/rest/api/2" and add v3 endpoint
            base_url = self.api_base_url.replace("/rest/api/2", "")
            
            # First, get the field information to determine the epic link field
            fields_endpoint = f"{base_url}/rest/api/3/field"
            async with aiohttp.ClientSession() as session:
                async with session.get(fields_endpoint, headers=self.headers, ssl=self.ssl_context) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get field information (v3): Status {response.status}")
                        return False
                    
                    fields = await response.json()
                    
            # Find the epic link field
            epic_link_field = None
            for field in fields:
                if field.get('name') == 'Epic Link':
                    epic_link_field = field.get('id')
                    break
            
            if not epic_link_field:
                logger.error("Could not find Epic Link field in JIRA instance (v3)")
                return False
                
            logger.info(f"Found Epic Link field (v3): {epic_link_field}")
            
            # Prepare update data - v3 API uses a different format
            update_data = {
                "fields": {
                    epic_link_field: epic_key
                }
            }
            
            # Send the update request
            endpoint = f"{base_url}/rest/api/3/issue/{issue_key}"
            headers = self.headers.copy()
            headers["Content-Type"] = "application/json"
            headers["Accept"] = "application/json"
            
            async with aiohttp.ClientSession() as session:
                async with session.put(endpoint, headers=headers, json=update_data, ssl=self.ssl_context) as response:
                    if response.status == 204 or response.status == 200:
                        logger.info(f"Successfully assigned issue {issue_key} to epic {epic_key} via v3 API")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to assign issue to epic via v3 API: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Exception during v3 API method: {str(e)}")
            return False

    async def remove_issue_from_epic(self, issue_key: str) -> bool:
        """
        Remove an issue from its epic (if it belongs to one).
        Args:
            issue_key (str): The key of the issue to remove from its epic.
        Returns:
            bool: True if the removal was successful, False otherwise.
        """
        try:
            logger.info(f"Removing issue {issue_key} from its epic")
            
            # Try multiple approaches in sequence
            
            # 1. First approach: Try direct field update with null value
            if await self._try_direct_epic_link_removal(issue_key):
                return True
            
            # 2. Second approach: Try delete property endpoint 
            if await self._try_delete_property(issue_key):
                return True
                
            # 3. Third approach: Try transitions
            if await self._try_transition_removal(issue_key):
                return True
                
            # 4. Fourth approach: Try REST API v3
            if await self._try_v3_api_removal(issue_key):
                return True
            
            logger.error(f"All attempts to remove issue {issue_key} from its epic failed")
            return False
            
        except Exception as e:
            logger.error(f"Exception while removing issue from epic: {str(e)}")
            return False
            
    async def _try_direct_epic_link_removal(self, issue_key):
        """Try direct field update to remove issue from epic"""
        try:
            # Get the epic link field
            epic_link_field = await self._get_epic_link_field()
            
            # Prepare update data with null value to remove the epic link
            update_data = {
                "fields": {
                    epic_link_field: None
                }
            }
            
            # Send the update request
            endpoint = f"{self.api_base_url}/issue/{issue_key}"
            async with aiohttp.ClientSession() as session:
                async with session.put(endpoint, headers=self.headers, json=update_data, ssl=self.ssl_context) as response:
                    if response.status == 204 or response.status == 200:
                        logger.info(f"Successfully removed issue {issue_key} from its epic via direct update")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to remove issue from epic via direct update: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Exception during direct epic link removal: {str(e)}")
            return False
            
    async def _try_delete_property(self, issue_key):
        """Try using the DELETE endpoint to remove the epic link property"""
        try:
            logger.info(f"Trying DELETE property method to remove issue {issue_key} from its epic")
            
            # Get the epic link field
            epic_link_field = await self._get_epic_link_field()
            
            # Use the DELETE endpoint to remove the property
            endpoint = f"{self.api_base_url}/issue/{issue_key}/properties/{epic_link_field}"
            async with aiohttp.ClientSession() as session:
                async with session.delete(endpoint, headers=self.headers, ssl=self.ssl_context) as response:
                    if response.status == 204 or response.status == 200:
                        logger.info(f"Successfully removed issue {issue_key} from its epic via DELETE property")
                        return True
                    else:
                        # Not found (404) could mean it's already not linked - consider it a success
                        if response.status == 404:
                            logger.info(f"Property not found, issue {issue_key} may not be linked to an epic")
                            return True
                            
                        error_text = await response.text()
                        logger.error(f"Failed to remove issue from epic via DELETE property: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Exception during DELETE property: {str(e)}")
            return False
            
    async def _try_transition_removal(self, issue_key):
        """Try using transitions to remove the epic link"""
        try:
            logger.info(f"Trying transition method to remove issue {issue_key} from its epic")
            
            # First, get available transitions for the issue
            transitions_endpoint = f"{self.api_base_url}/issue/{issue_key}/transitions"
            async with aiohttp.ClientSession() as session:
                async with session.get(transitions_endpoint, headers=self.headers, ssl=self.ssl_context) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get transitions: Status {response.status}")
                        return False
                    
                    transitions_data = await response.json()
                    transitions = transitions_data.get("transitions", [])
                    
                    if not transitions:
                        logger.error(f"No transitions available for issue {issue_key}")
                        return False
                    
                    # Use the first transition (usually "In Progress")
                    transition_id = transitions[0].get("id")
            
            # Get the epic link field
            epic_link_field = await self._get_epic_link_field()
            
            # Prepare transition data with null value to remove the epic link
            transition_data = {
                "transition": {
                    "id": transition_id
                },
                "fields": {
                    epic_link_field: None
                }
            }
            
            # Send the transition request
            endpoint = f"{self.api_base_url}/issue/{issue_key}/transitions"
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=self.headers, json=transition_data, ssl=self.ssl_context) as response:
                    if response.status == 204 or response.status == 200:
                        logger.info(f"Successfully removed issue {issue_key} from its epic via transition")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to remove issue from epic via transition: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Exception during transition removal: {str(e)}")
            return False
            
    async def _try_v3_api_removal(self, issue_key):
        """Try using the REST API v3 to remove the epic link"""
        try:
            logger.info(f"Trying REST API v3 method to remove issue {issue_key} from its epic")
            
            # Get base API URL without "/rest/api/2" and add v3 endpoint
            base_url = self.api_base_url.replace("/rest/api/2", "")
            
            # First, get the field information to determine the epic link field
            fields_endpoint = f"{base_url}/rest/api/3/field"
            async with aiohttp.ClientSession() as session:
                async with session.get(fields_endpoint, headers=self.headers, ssl=self.ssl_context) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get field information (v3): Status {response.status}")
                        return False
                    
                    fields = await response.json()
                    
            # Find the epic link field
            epic_link_field = None
            for field in fields:
                if field.get('name') == 'Epic Link':
                    epic_link_field = field.get('id')
                    break
            
            if not epic_link_field:
                logger.error("Could not find Epic Link field in JIRA instance (v3)")
                return False
                
            logger.info(f"Found Epic Link field (v3): {epic_link_field}")
            
            # Prepare update data with null value to remove the epic link
            update_data = {
                "fields": {
                    epic_link_field: None
                }
            }
            
            # Send the update request
            endpoint = f"{base_url}/rest/api/3/issue/{issue_key}"
            headers = self.headers.copy()
            headers["Content-Type"] = "application/json"
            headers["Accept"] = "application/json"
            
            async with aiohttp.ClientSession() as session:
                async with session.put(endpoint, headers=headers, json=update_data, ssl=self.ssl_context) as response:
                    if response.status == 204 or response.status == 200:
                        logger.info(f"Successfully removed issue {issue_key} from its epic via v3 API")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to remove issue from epic via v3 API: Status {response.status}")
                        logger.error(f"Response: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Exception during v3 API removal: {str(e)}")
            return False

    async def update_epic_details(self, epic_key: str, summary: str = None, description: str = None, status: str = None) -> bool:
        """
        Update the details of an epic in JIRA.

        :param epic_key: The JIRA issue key for the epic.
        :param summary: The new summary for the epic.
        :param description: The new description for the epic.
        :param status: The new status for the epic.
        :return: True if the update was successful, False otherwise.
        """
        self.logger.info(f"Updating epic {epic_key} with new details.")

        update_data = {}
        if summary:
            update_data['summary'] = summary
        if description:
            update_data['description'] = description
        if status:
            update_data['status'] = status

        if not update_data:
            self.logger.warning("No update data provided for epic.")
            return False

        url = f"{self.api_base_url}/issue/{epic_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, json={'fields': update_data}, headers=self.headers, ssl=self.ssl_context) as response:
                    if response.status == HTTPStatus.NO_CONTENT:
                        self.logger.info(f"Epic {epic_key} updated successfully.")
                        return True
                    else:
                        self.logger.error(f"Failed to update epic {epic_key}. Status: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"Exception occurred while updating epic {epic_key}: {e}")
            return False
