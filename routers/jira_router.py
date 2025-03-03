from typing import List

from fastapi import APIRouter

from models import (
    TicketCreateRequest,
    TicketCreateResponse,
    JiraTicketDetails,
    JiraProject
)
from jira_integration.jira_service import JiraService

router = APIRouter()

# Initialize JIRA service
jira_service = JiraService()


@router.post("/tickets/", response_model=TicketCreateResponse)
async def create_ticket(ticket: TicketCreateRequest) -> TicketCreateResponse:
    """Create a new JIRA ticket with all optional fields and relationships"""
    return await jira_service.create_ticket(
        project_key=ticket.project_key,
        summary=ticket.summary,
        description=ticket.description,
        issue_type=ticket.issue_type,
        parent_key=ticket.parent_key,
        story_points=ticket.story_points,
        labels=ticket.labels,
        acceptance_criteria=ticket.acceptance_criteria,
        technical_domain=ticket.technical_domain,
        epic_link=ticket.epic_link,
        priority=ticket.priority
    )


@router.get("/tickets/{ticket_key}", response_model=JiraTicketDetails)
async def get_ticket(ticket_key: str) -> JiraTicketDetails:
    """Get details of a specific JIRA ticket"""
    return await jira_service.get_ticket(ticket_key)


@router.get("/projects", response_model=List[JiraProject])
async def get_projects() -> List[JiraProject]:
    """Get list of available JIRA projects"""
    return await jira_service.get_projects()
