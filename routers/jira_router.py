from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.jira_service import JiraService
from typing import Dict, Any, List

router = APIRouter()

class TicketCreate(BaseModel):
    project_key: str
    summary: str
    description: str
    issue_type: str = "Task"

# Initialize JIRA service
jira_service = JiraService()

@router.post("/tickets/", response_model=Dict[str, str])
async def create_ticket(ticket: TicketCreate):
    """Create a new JIRA ticket"""
    return jira_service.create_ticket(
        project_key=ticket.project_key,
        summary=ticket.summary,
        description=ticket.description,
        issue_type=ticket.issue_type
    )

@router.get("/tickets/{ticket_key}", response_model=Dict[str, Any])
async def get_ticket(ticket_key: str):
    """Get details of a specific JIRA ticket"""
    return jira_service.get_ticket(ticket_key)

@router.get("/projects", response_model=List[Dict[str, str]])
async def get_projects():
    """Get list of available JIRA projects"""
    return jira_service.get_projects() 