from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List
from services.jira_breakdown_service import JiraBreakdownService
from services.jira_orchestration_service import JiraOrchestrationService
from services.response_formatter_service import ResponseFormatterService
from services.revision_service import RevisionService
from config.database import DATABASE
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
import sqlite3

router = APIRouter()
jira_breakdown_service = JiraBreakdownService()
jira_orchestration_service = JiraOrchestrationService()
response_formatter = ResponseFormatterService()
revision_service = RevisionService()

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

@router.post("/break-down-epic/{epic_key}", response_model=JiraEpicBreakdownResult)
async def break_down_epic(epic_key: str) -> JiraEpicBreakdownResult:
    """Break down a JIRA epic into smaller tasks"""
    try:
        result = await jira_breakdown_service.break_down_epic(epic_key)
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

@router.post("/revise-plan/")
async def request_plan_revision(request: RevisionRequest) -> RevisionConfirmation:
    try:
        logger.info(f"Received revision request for execution: {request.execution_id}")
        logger.debug(f"Request data: {request.dict()}")
        
        # Validate the request has content
        if not request.revision_request.strip():
            raise HTTPException(
                status_code=400,
                detail="Revision request cannot be empty"
            )
        
        # Get execution record to get epic_key
        execution = await revision_service.execution_tracker.get_execution_record(request.execution_id)
        
        # Generate a temporary revision ID
        temp_revision_id = str(uuid7())
        
        # Add more logging
        logger.debug("Calling interpret_revision_request...")
        interpreted_changes = await revision_service.interpret_revision_request(
            execution_id=request.execution_id,
            revision_request=request.revision_request
        )
        
        logger.debug(f"Got interpreted changes: {interpreted_changes}")
        
        await revision_service.store_revision_request(
            temp_revision_id=temp_revision_id,
            original_execution_id=request.execution_id,
            interpreted_changes=interpreted_changes,
            epic_key=execution.epic_key  # Pass the epic_key from execution record
        )
        
        return RevisionConfirmation(
            original_execution_id=request.execution_id,
            interpreted_changes=interpreted_changes,
            temp_revision_id=temp_revision_id
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
        # No need to convert to uuid7, use string directly
        revision = await revision_service.confirm_revision_request(
            temp_revision_id=temp_revision_id,
            accepted=accept
        )
        
        if not accept:
            return RevisionConfirmation(
                original_execution_id=revision.execution_id,  # Already a string
                interpreted_changes=revision.changes_interpreted,
                confirmation_required=False,
                temp_revision_id=temp_revision_id,
                status="REJECTED"
            )
        
        return RevisionConfirmation(
            original_execution_id=revision.execution_id,  # Already a string
            interpreted_changes=revision.changes_interpreted,
            confirmation_required=False,
            temp_revision_id=temp_revision_id,
            status="ACCEPTED"
        )
        
    except Exception as e:
        logger.error(f"Failed to confirm revision request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm revision request: {str(e)}"
        )

@router.post("/apply-revision/{temp_revision_id}")
async def apply_revision(
    temp_revision_id: str
) -> RevisionResponse:
    """Apply the confirmed changes and generate new execution plan"""
    try:
        # Use string directly
        revision = await revision_service.get_revision_details(temp_revision_id)
        if not revision.accepted:
            raise HTTPException(
                status_code=400,
                detail="Cannot apply revision that hasn't been accepted"
            )
        
        # Generate new execution id as string
        new_execution_id = str(uuid7())
        new_plan = await revision_service.apply_revision(
            original_execution_id=revision.execution_id,
            interpreted_changes=revision.interpreted_changes,
            new_execution_id=new_execution_id
        )
        
        return RevisionResponse(
            original_execution_id=revision.execution_id,
            new_execution_id=new_execution_id,
            changes_made=revision.interpreted_changes,
            new_plan_file=new_plan.filename
        )
        
    except Exception as e:
        logger.error(f"Failed to apply revision: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply revision: {str(e)}"
        )

@router.get(
    "/debug/executions",
    summary="Debug endpoint to view execution records",
    description="Lists all execution records in the database"
)
async def list_executions():
    """List all execution records for debugging"""
    try:
        with sqlite3.connect(DATABASE["sqlite"]["path"]) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM executions ORDER BY created_at DESC")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return {
                "executions": [
                    dict(zip(columns, row))
                    for row in rows
                ]
            }
    except Exception as e:
        logger.error(f"Failed to list executions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list executions: {str(e)}"
        )

@router.get(
    "/debug/revisions",
    summary="Debug endpoint to view revision records",
    description="Lists all revision records in the database"
)
async def list_revisions():
    """List all revision records for debugging"""
    try:
        with sqlite3.connect(DATABASE["sqlite"]["path"]) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM revisions ORDER BY created_at DESC")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return {
                "revisions": [
                    dict(zip(columns, row))
                    for row in rows
                ]
            }
    except Exception as e:
        logger.error(f"Failed to list revisions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list revisions: {str(e)}"
        )

@router.get("/debug/executions/{execution_id}")
async def get_execution_details(execution_id: str):
    """Get execution record and its revision history by ID"""
    try:
        with sqlite3.connect(DATABASE["sqlite"]["path"]) as conn:
            cursor = conn.cursor()
            
            # Get execution record
            cursor.execute("""
                SELECT * FROM executions 
                WHERE execution_id = ?
            """, (execution_id,))
            columns = [description[0] for description in cursor.description]
            execution_row = cursor.fetchone()
            
            if not execution_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"No execution found with ID: {execution_id}"
                )
            
            # Get revision history
            cursor.execute("""
                SELECT * FROM revisions 
                WHERE execution_id = ? 
                ORDER BY created_at DESC
            """, (execution_id,))
            revision_columns = [description[0] for description in cursor.description]
            revision_rows = cursor.fetchall()
            
            return {
                "execution": dict(zip(columns, execution_row)),
                "revisions": [
                    dict(zip(revision_columns, row))
                    for row in revision_rows
                ]
            }
            
    except Exception as e:
        logger.error(f"Failed to get execution details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution details: {str(e)}"
        ) 