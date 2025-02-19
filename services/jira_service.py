from utils import bootstrap  # This must be the first import
import aiohttp  # Replace requests with aiohttp
import os
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
import logging
import base64
import ssl
from models import TicketCreateResponse, JiraProject
from models.jira_ticket_details import JiraTicketDetails
from loguru import logger
from jira_integration import EpicOperations, TicketOperations  # Updated import path

logger = logging.getLogger(__name__)

class JiraService:
    """Service for interacting with JIRA"""
    
    def __init__(self):
        """Initialize JIRA operations"""
        self.epic_ops = EpicOperations()
        self.ticket_ops = TicketOperations()
        
        self.base_url = f"{os.getenv('JIRA_SERVER')}/rest/api/2"
        
        self.set_headers_basic()
        
        # Create SSL context that doesn't verify
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def set_headers(self):
        self.headers = {
            "Authorization": f"Bearer {os.getenv('JIRA_API_TOKEN')}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def set_headers_basic(self):
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
        """Get a ticket by key"""
        try:
            logger.info(f"Attempting to fetch ticket: {ticket_key}")
            
            # Check if it's an epic based on key format
            is_epic = ticket_key.split("-")[1].startswith("E")
            logger.debug(f"Ticket {ticket_key} is_epic: {is_epic}")
            
            if is_epic:
                logger.info(f"Fetching epic details for {ticket_key}")
                ticket_data = await self.epic_ops.get_epic_details(ticket_key)
                if ticket_data is None:
                    logger.error(f"Epic {ticket_key} details returned None")
                    return None
            else:
                logger.info(f"Fetching regular ticket details for {ticket_key}")
                ticket_data = await self.ticket_ops.get_ticket_details(ticket_key)
                
            if not ticket_data:
                logger.warning(f"No data found for ticket {ticket_key}")
                return None
                
            logger.debug(f"Raw ticket data received: {ticket_data}")
                
            # Convert raw JIRA data to JiraTicketDetails model
            try:
                ticket_details = JiraTicketDetails(
                    key=ticket_data["key"],
                    summary=ticket_data["summary"],
                    description=ticket_data.get("description", ""),
                    issue_type=ticket_data.get("issuetype", {}).get("name", "Unknown"),
                    status=ticket_data.get("status", {}).get("name", "Unknown"),
                    project_key=ticket_data.get("project", {}).get("key", ""),
                    created=ticket_data["created"],
                    updated=ticket_data["updated"],
                    assignee=ticket_data.get("assignee", {}).get("name"),
                    reporter=ticket_data.get("reporter", {}).get("name"),
                    priority=ticket_data.get("priority", {}).get("name"),
                    labels=ticket_data.get("labels", []),
                    components=[c["name"] for c in ticket_data.get("components", [])],
                    parent_key=ticket_data.get("parent", {}).get("key"),
                    epic_key=ticket_data.get("customfield_10014"),  # Assuming this is the epic link field
                    story_points=ticket_data.get("customfield_10016"),  # Assuming this is the story points field
                    custom_fields={
                        k: v for k, v in ticket_data.items()
                        if k.startswith("customfield_") and v is not None
                    }
                )
                logger.info(f"Successfully converted ticket {ticket_key} to JiraTicketDetails")
                return ticket_details
            except Exception as e:
                logger.error(f"Failed to convert ticket data to JiraTicketDetails: {str(e)}")
                logger.error(f"Problematic ticket data: {ticket_data}")
                raise
                
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_key}: {str(e)}")
            logger.exception("Full traceback:")
            return None
    
    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new ticket based on type"""
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
                    raise ValueError("Parent key is required for subtasks")
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
            logger.error(f"Ticket data: {ticket_data}")
            raise
    
    async def update_ticket(
        self,
        ticket_key: str,
        fields: Dict[str, Any]
    ) -> bool:
        """Update a ticket's fields"""
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
        """Update a ticket's status"""
        try:
            if ticket_key.split("-")[1].startswith("E"):
                return await self.epic_ops.update_epic_status(ticket_key, status)
            else:
                return await self.ticket_ops.update_ticket_status(ticket_key, status)
        except Exception as e:
            logger.error(f"Failed to update ticket status: {str(e)}")
            return False
    
    async def get_epic_progress(self, epic_key: str) -> Dict[str, Any]:
        """Get progress statistics for an epic"""
        return await self.epic_ops.get_epic_progress(epic_key)
    
    async def get_linked_tickets(
        self,
        ticket_key: str,
        link_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get tickets linked to the specified ticket"""
        return await self.ticket_ops.get_linked_tickets(ticket_key, link_type)

    async def get_projects(self) -> List[JiraProject]:
        """Get list of available JIRA projects"""
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