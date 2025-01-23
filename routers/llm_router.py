from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from services.jira_breakdown_service import JiraBreakdownService
from services.jira_orchestration_service import JiraOrchestrationService
from models import (
    TicketGenerationRequest,
    TicketGenerationResponse,
    ComplexityAnalysisRequest,
    ComplexityAnalysisResponse,
    EpicBreakdownResponse
)
from loguru import logger

router = APIRouter()
jira_breakdown_service = JiraBreakdownService()
jira_orchestration_service = JiraOrchestrationService()

@router.post(
    "/generate-description/", 
    response_model=TicketGenerationResponse,
    status_code=200,
    summary="Generate JIRA ticket description",
    description="Generate a structured JIRA ticket description using LLM"
)
async def generate_ticket_description(request: TicketGenerationRequest):
    """Generate a JIRA ticket description using LLM"""
    return await jira_breakdown_service.generate_ticket_description(
        context=request.context,
        requirements=request.requirements,
        additional_info=request.additional_info
    )

@router.post(
    "/analyze-complexity/", 
    response_model=ComplexityAnalysisResponse,
    status_code=200,
    summary="Analyze ticket complexity",
    description="Analyze the complexity of a JIRA ticket"
)
async def analyze_ticket_complexity(request: ComplexityAnalysisRequest):
    """Analyze the complexity of a ticket"""
    return await jira_breakdown_service.analyze_ticket_complexity(
        ticket_description=request.ticket_description
    )

@router.post(
    "/break-down-epic/{epic_key}", 
    response_model=EpicBreakdownResponse,
    status_code=200,
    summary="Break down epic",
    description="Break down a JIRA epic into smaller tasks"
)
async def break_down_epic(epic_key: str):
    """Break down a JIRA epic into smaller tasks"""
    logger.info(f"Received request to break down epic: {epic_key}")
    return await jira_breakdown_service.break_down_epic(epic_key)

@router.post(
    "/create-epic-subtasks/{epic_key}", 
    response_model=EpicBreakdownResponse,
    status_code=200,
    summary="Create epic subtasks",
    description="Break down an epic and optionally create the subtasks in JIRA"
)
async def create_epic_subtasks(
    epic_key: str,
    create_in_jira: bool = False,
    dry_run: bool = False
):
    """Break down an epic and optionally create the subtasks in JIRA"""
    logger.info(f"Received request to create subtasks for epic: {epic_key}")
    logger.debug(f"Create in JIRA: {create_in_jira}, Dry run: {dry_run}")
    
    breakdown = await jira_breakdown_service.break_down_epic(epic_key)
    
    if dry_run:
        execution_plan = await jira_orchestration_service.create_execution_plan(
            epic_key, 
            breakdown
        )
        breakdown["execution_plan"] = execution_plan
    elif create_in_jira:
        created_tasks = await jira_orchestration_service.create_epic_breakdown_structure(
            epic_key, 
            breakdown
        )
        breakdown["created_jira_tasks"] = created_tasks
    
    return breakdown 