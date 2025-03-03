import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from breakdown import ExecutionManager
from models import (
    TicketGenerationRequest,
    TicketGenerationResponse,
    ComplexityAnalysisRequest,
    ComplexityAnalysisResponse,
    JiraEpicBreakdownResult,
    RevisionRequest,
    RevisionConfirmation,
    RevisionResponse
)
from services.jira_orchestration_service import JiraOrchestrationService
from services.mongodb_service import MongoDBService
from services.response_formatter_service import ResponseFormatterService
from services.revision_service import RevisionService

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
    execution_manager = ExecutionManager(request.epic_key)
    return await execution_manager.epic_analyzer.generate_ticket_description(
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
    execution_manager = ExecutionManager(request.epic_key)
    return await execution_manager.epic_analyzer.analyze_complexity(
        ticket_description=request.ticket_description
    )


@router.post("/break-down-epic/{epic_key}", response_model=JiraEpicBreakdownResult)
async def break_down_epic(epic_key: str) -> JiraEpicBreakdownResult:
    """Break down a JIRA epic into smaller tasks"""
    try:
        execution_manager = ExecutionManager(epic_key)
        response_formatter = ResponseFormatterService()
        result = await execution_manager.execute_breakdown()
        logger.info(f"Breakdown result: {result}")
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

    execution_manager = ExecutionManager(epic_key)
    jira_orchestration_service = JiraOrchestrationService()
    breakdown = await execution_manager.execute_breakdown()

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
    """Request a revision to a ticket"""
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

        try:
            # Initialize revision service
            revision_service = RevisionService()

            # Add more logging
            logger.debug("Calling interpret_revision_request...")
            interpreted_changes = await revision_service.interpret_revision_request(
                execution_id=execution_id,
                ticket_id=ticket_id,
                revision_request=request.revision_request,
                epic_key=epic_key
            )

            logger.debug(f"Got interpreted changes: {interpreted_changes}")

            # Create revision record
            revision = await revision_service.create_revision(
                execution_id=execution_id,
                ticket_id=ticket_id,
                changes_requested=request.revision_request,
                changes_interpreted=interpreted_changes,
                epic_key=epic_key
            )

            return RevisionConfirmation(
                original_execution_id=execution_id,
                ticket_id=ticket_id,
                interpreted_changes=interpreted_changes,
                temp_revision_id=revision.revision_id
            )

        except Exception as e:
            logger.error(f"Internal error processing revision: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal error processing revision: {str(e)}"
            )

    except HTTPException as http_ex:
        logger.error(f"HTTP error in request_plan_revision: {http_ex.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in request_plan_revision: {str(e)}")
        logger.error(f"Request data: {request if request else 'No request data'}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error processing revision request: {str(e)}"
        )


@router.post("/confirm-revision-request/{temp_revision_id}")
async def confirm_revision_request(
        temp_revision_id: str,
        accept: bool = Query(True, description="Whether to accept or reject the revision")
) -> RevisionConfirmation:
    """Confirm or reject a revision request"""
    try:
        # Initialize MongoDB service
        mongodb_service = MongoDBService()

        # Get the revision record
        revision = mongodb_service.get_revision(temp_revision_id)
        if not revision:
            raise HTTPException(
                status_code=404,
                detail=f"No revision found with ID: {temp_revision_id}"
            )

        # Get epic key from the revision record - access as attribute instead of using .get()
        epic_key = revision.epic_key
        if not epic_key:
            raise HTTPException(
                status_code=500,
                detail=f"Epic key not found in revision record: {temp_revision_id}"
            )

        try:
            # Initialize revision service
            revision_service = RevisionService()

            # Update revision status
            await revision_service.update_revision_status(
                revision_id=temp_revision_id,
                status="ACCEPTED" if accept else "REJECTED",
                accepted=accept
            )

            return RevisionConfirmation(
                original_execution_id=revision.execution_id,
                interpreted_changes=revision.changes_interpreted,
                confirmation_required=False,
                temp_revision_id=temp_revision_id,
                status="ACCEPTED" if accept else "REJECTED"
            )

        except Exception as e:
            logger.error(f"Internal error confirming revision: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal error confirming revision: {str(e)}"
            )

    except HTTPException as http_ex:
        logger.error(f"HTTP error in confirm_revision_request: {http_ex.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in confirm_revision_request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error confirming revision: {str(e)}"
        )


@router.post("/apply-revision/{temp_revision_id}")
async def apply_revision(
        temp_revision_id: str
) -> RevisionResponse:
    """Apply the accepted revision changes to the ticket"""
    try:
        # Initialize MongoDB service
        mongodb_service = MongoDBService()

        # Get the revision record
        revision = mongodb_service.get_revision(temp_revision_id)
        if not revision:
            raise HTTPException(
                status_code=404,
                detail=f"No revision found with ID: {temp_revision_id}"
            )

        # Check revision state - access attributes directly instead of using .get()
        current_status = revision.status
        if current_status == "APPLIED":
            raise HTTPException(
                status_code=409,
                detail=f"Revision has already been applied. Current state: {current_status}"
            )
        elif current_status != "ACCEPTED":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot apply revision that is not in ACCEPTED state. Current state: {current_status}"
            )

        try:
            # Initialize revision service
            revision_service = RevisionService()

            # Apply the changes using the revision ID
            logger.debug("Applying revision changes...")
            changes_made = await revision_service.apply_revision_changes(
                revision_id=temp_revision_id
            )

            # Update revision status to APPLIED
            await revision_service.update_revision_status(
                revision_id=temp_revision_id,
                status="APPLIED"
            )

            return RevisionResponse(
                original_execution_id=revision.execution_id,
                new_execution_id=revision.execution_id,  # Same execution ID since we're modifying in place
                changes_made=changes_made,
                new_plan_file=revision.execution_plan_file
            )

        except Exception as e:
            logger.error(f"Internal error applying revision changes: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal error applying revision changes: {str(e)}"
            )

    except HTTPException as http_ex:
        logger.error(f"HTTP error in apply_revision: {http_ex.detail}")
        raise  # Just raise, don't re-raise
    except Exception as e:
        logger.error(f"Unexpected error in apply_revision: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error applying revision: {str(e)}"
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

