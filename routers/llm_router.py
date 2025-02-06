from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List
from services.jira_breakdown_service import JiraBreakdownService
from services.jira_orchestration_service import JiraOrchestrationService
from services.response_formatter_service import ResponseFormatterService
from services.revision_service import RevisionService
from uuid_extensions import uuid7
from models import (
    TicketGenerationRequest,
    TicketGenerationResponse,
    ComplexityAnalysisRequest,
    ComplexityAnalysisResponse,
    JiraEpicBreakdownResult,
    JiraTaskDefinition,
    RevisionRequest,
    RevisionConfirmation,
    RevisionResponse
)
from loguru import logger
from datetime import datetime
import os
import yaml
from services.mongodb_service import MongoDBService

router = APIRouter()

@router.post(
    "/generate-description/", 
    response_model=TicketGenerationResponse,
    status_code=200,
    summary="Generate JIRA ticket description",
    description="Generate a structured JIRA ticket description using LLM"
)
async def generate_ticket_description(request: TicketGenerationRequest):
    """Generate a JIRA ticket description using LLM"""
    jira_breakdown_service = JiraBreakdownService(request.epic_key)
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
    jira_breakdown_service = JiraBreakdownService(request.epic_key)
    return await jira_breakdown_service.analyze_ticket_complexity(
        ticket_description=request.ticket_description
    )

@router.post("/break-down-epic/{epic_key}", response_model=JiraEpicBreakdownResult)
async def break_down_epic(epic_key: str) -> JiraEpicBreakdownResult:
    """Break down a JIRA epic into smaller tasks"""
    try:
        jira_breakdown_service = JiraBreakdownService(epic_key)
        response_formatter = ResponseFormatterService()
        result = await jira_breakdown_service.break_down_epic()
        return response_formatter.format_epic_breakdown(result)
        
    except Exception as e:
        logger.error(f"Failed to break down epic {epic_key}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to break down epic: {str(e)}"
        )

@router.post(
    "/create-epic-subtasks/{epic_key}", 
    response_model=JiraEpicBreakdownResult,
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
    
    jira_breakdown_service = JiraBreakdownService(epic_key)
    jira_orchestration_service = JiraOrchestrationService()
    breakdown = await jira_breakdown_service.break_down_epic()
    
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

@router.post("/revise-plan/{execution_id}/ticket/{ticket_id}")
async def request_plan_revision(
    execution_id: str,
    ticket_id: str,
    request: RevisionRequest
) -> RevisionConfirmation:
    try:
        logger.info(f"Received revision request for execution: {execution_id}, ticket: {ticket_id}")
        logger.debug(f"Request data: {request.model_dump()}")
        
        # Validate the request has content
        if not request.revision_request.strip():
            raise HTTPException(
                status_code=400,
                detail="Revision request cannot be empty"
            )
        
        # Initialize MongoDB service and get the specific ticket
        mongodb_service = MongoDBService()
        target_ticket = mongodb_service.get_ticket_by_execution_and_id(execution_id, ticket_id)
        
        if not target_ticket:
            raise HTTPException(
                status_code=404,
                detail=f"Ticket {ticket_id} not found in execution {execution_id}"
            )
        
        # Get epic key from the ticket
        epic_key = target_ticket.epic_key
        
        # Initialize revision service with epic key
        revision_service = RevisionService(epic_key)
        
        # Generate a temporary revision ID
        temp_revision_id = str(uuid7())
        
        # Add more logging
        logger.debug("Calling interpret_revision_request...")
        interpreted_changes = await revision_service.interpret_revision_request(
            execution_id=execution_id,
            ticket_id=ticket_id,
            revision_request=request.revision_request
        )
        
        logger.debug(f"Got interpreted changes: {interpreted_changes}")
        
        # Create revision record
        revision = await revision_service.create_revision(
            execution_id=execution_id,
            ticket_id=ticket_id,
            changes_requested=request.revision_request,
            changes_interpreted=interpreted_changes
        )
        
        return RevisionConfirmation(
            original_execution_id=execution_id,
            ticket_id=ticket_id,
            interpreted_changes=interpreted_changes,
            temp_revision_id=revision.revision_id
        )
        
    except Exception as e:
        logger.error(f"Failed to process revision request: {str(e)}")
        logger.error(f"Request data: {request if request else 'No request data'}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process revision request: {str(e)}"
        )

@router.post("/confirm-revision-request/{temp_revision_id}")
async def confirm_revision_request(
    temp_revision_id: str,
    accept: bool = True
) -> RevisionConfirmation:
    """Confirm whether the interpreted changes are correct"""
    try:
        # Initialize MongoDB service
        mongodb_service = MongoDBService()
        
        # Find the execution plan file that contains this revision ID
        execution_plans_dir = "execution_plans"
        epic_key = None
        for filename in os.listdir(execution_plans_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(execution_plans_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                    if temp_revision_id in content:
                        # Extract epic key from filename (format: EXECUTION_EPIC-KEY_timestamp.md)
                        parts = filename.split('_')
                        if len(parts) > 1:
                            epic_key = parts[1]
                            break
        
        if not epic_key:
            raise HTTPException(
                status_code=404,
                detail=f"No revision found with ID: {temp_revision_id}"
            )
        
        # Initialize revision service with epic key
        revision_service = RevisionService(epic_key)
        
        # Update revision status
        await revision_service.update_revision_status(
            revision_id=temp_revision_id,
            status="ACCEPTED" if accept else "REJECTED",
            accepted=accept
        )
        
        return RevisionConfirmation(
            original_execution_id="",  # This will be filled from the execution plan
            interpreted_changes="",    # This will be filled from the execution plan
            confirmation_required=False,
            temp_revision_id=temp_revision_id,
            status="ACCEPTED" if accept else "REJECTED"
        )
        
    except Exception as e:
        logger.error(f"Failed to confirm revision request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm revision request: {str(e)}"
        )

@router.get(
    "/debug/executions",
    summary="Debug endpoint to list execution plans",
    description="Lists all execution plan files"
)
async def list_executions():
    """List all execution plan files for debugging"""
    try:
        execution_plans_dir = "execution_plans"
        executions = []
        
        if os.path.exists(execution_plans_dir):
            for filename in os.listdir(execution_plans_dir):
                if filename.startswith("EXECUTION_") and filename.endswith(".md"):
                    filepath = os.path.join(execution_plans_dir, filename)
                    stat = os.stat(filepath)
                    
                    # Parse filename for metadata (format: EXECUTION_EPIC-KEY_timestamp.md)
                    parts = filename.split('_')
                    if len(parts) > 2:
                        epic_key = parts[1]
                        timestamp = parts[2].replace('.md', '')
                        
                        executions.append({
                            "filename": filename,
                            "epic_key": epic_key,
                            "created_at": timestamp,
                            "file_size": stat.st_size,
                            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
        
        return {
            "executions": sorted(executions, key=lambda x: x["created_at"], reverse=True)
        }
        
    except Exception as e:
        logger.error(f"Failed to list executions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list executions: {str(e)}"
        ) 