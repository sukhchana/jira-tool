from utils import bootstrap  # This must be the first import
import aiohttp  # Replace requests with aiohttp
import os
from typing import Dict, Any, List
from fastapi import HTTPException
import logging
import base64
import ssl
from models import TicketCreateResponse, JiraProject

logger = logging.getLogger(__name__)

class JiraService:
    def __init__(self):
        """Initialize JIRA service with proper authentication"""
        self.base_url = f"{os.getenv('JIRA_SERVER')}/rest/api/2"
        
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
        
        # Create SSL context that doesn't verify
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        logger.debug(f"Initialized JIRA service for user: {email}")

    async def get_ticket(self, ticket_key: str) -> Dict[str, Any]:
        """Get details of a specific JIRA ticket"""
        try:
            url = f"{self.base_url}/issue/{ticket_key}"
            logger.debug(f"Attempting to fetch ticket from: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers,
                    ssl=self.ssl_context  # Disable SSL verification
                ) as response:
                    if response.status == 200:
                        issue_data = await response.json()
                        fields = issue_data.get("fields", {})
                        
                        return {
                            "key": issue_data.get("key"),
                            "summary": fields.get("summary"),
                            "description": fields.get("description"),
                            "status": fields.get("status", {}).get("name"),
                            "created": fields.get("created"),
                            "updated": fields.get("updated")
                        }
                    elif response.status == 404:
                        error_msg = (
                            f"Ticket {ticket_key} not found\n"
                            f"API URL: {url}\n"
                            f"JIRA Server: {os.getenv('JIRA_SERVER')}\n"
                            f"Response: {await response.text()}"
                        )
                        raise HTTPException(status_code=404, detail=error_msg)
                    else:
                        error_msg = (
                            f"JIRA API Error:\n"
                            f"URL: {url}\n"
                            f"Status Code: {response.status}\n"
                            f"Response: {await response.text()}"
                        )
                        raise HTTPException(
                            status_code=response.status,
                            detail=error_msg
                        )
                        
        except aiohttp.ClientError as e:
            error_msg = (
                f"Failed to fetch ticket {ticket_key}:\n"
                f"URL: {url}\n"
                f"Error: {str(e)}"
            )
            raise HTTPException(status_code=500, detail=error_msg)

    async def create_ticket(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str,
        *,
        parent_key: str = None,
        story_points: int = None,
        labels: List[str] = None,
        acceptance_criteria: str = None,
        technical_domain: str = None,
        epic_link: str = None,
        priority: str = "Medium"
    ) -> TicketCreateResponse:
        """Create a new JIRA ticket with relationships and custom fields"""
        try:
            url = f"{self.base_url}/issue"
            
            # Build the base fields
            fields = {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
                "priority": {"name": priority}
            }
            
            # Add parent link for subtasks
            if parent_key and issue_type == "Sub-task":
                fields["parent"] = {"key": parent_key}
            
            # Add epic link for stories and technical tasks
            if epic_link and issue_type in ["Story", "Task"]:
                fields["customfield_10014"] = epic_link  # Epic Link field
            
            # Add story points if provided
            if story_points is not None:
                fields["customfield_10016"] = float(story_points)  # Story Points field
            
            # Add labels
            if labels:
                fields["labels"] = labels
                if technical_domain and technical_domain not in labels:
                    fields["labels"].append(technical_domain)
            elif technical_domain:
                fields["labels"] = [technical_domain]
            
            # Add acceptance criteria if provided
            if acceptance_criteria:
                fields["customfield_10015"] = acceptance_criteria  # Acceptance Criteria field
            
            payload = {"fields": fields}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    headers=self.headers,
                    json=payload,
                    ssl=self.ssl_context
                ) as response:
                    if response.status == 201:
                        issue_data = await response.json()
                        issue_key = issue_data.get("key")
                        return TicketCreateResponse(
                            status="success",
                            message="Ticket created successfully",
                            ticket_key=issue_key,
                            ticket_url=f"{os.getenv('JIRA_SERVER')}/browse/{issue_key}"
                        )
                    else:
                        error_msg = (
                            f"Failed to create JIRA ticket:\n"
                            f"Status: {response.status}\n"
                            f"Response: {await response.text()}"
                        )
                        raise HTTPException(status_code=response.status, detail=error_msg)
                    
        except Exception as e:
            logger.error(f"Failed to create ticket: {str(e)}")
            raise

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