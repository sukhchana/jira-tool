from typing import Dict, Any, Optional, List
from uuid_extensions import uuid7
from datetime import datetime
from loguru import logger
from dataclasses import dataclass
from database.mongodb_handlers import ExecutionsHandler, RevisionsHandler
from models.mongodb_models import ExecutionModel, RevisionModel

@dataclass
class ExecutionRecord:
    execution_id: str
    epic_key: str
    execution_plan_file: str
    proposed_plan_file: str
    status: str
    created_at: datetime
    parent_execution_id: Optional[str] = None

@dataclass
class RevisionRecord:
    revision_id: str
    execution_id: str
    proposed_plan_file: str
    execution_plan_file: str
    status: str  # PENDING, ACCEPTED, REJECTED, APPLIED
    created_at: datetime
    changes_requested: str
    changes_interpreted: str
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None

class ExecutionTrackerService:
    """Service for tracking execution plans and their revisions"""
    
    def __init__(self):
        """Initialize the tracker service with MongoDB handlers"""
        self.executions = ExecutionsHandler()
        self.revisions = RevisionsHandler()
        logger.info("Initialized ExecutionTrackerService with MongoDB")
    
    async def create_execution_record(
        self,
        execution_id: str,
        epic_key: str,
        execution_plan_file: str,
        proposed_plan_file: str,
        parent_execution_id: Optional[str] = None,
        status: str = "ACTIVE"
    ) -> ExecutionRecord:
        """Create a new execution record"""
        try:
            logger.info("=== Creating Execution Record ===")
            logger.info(f"Parameters received:")
            logger.info(f"execution_id: {execution_id}")
            logger.info(f"epic_key: {epic_key}")
            logger.info(f"execution_plan_file: {execution_plan_file}")
            logger.info(f"proposed_plan_file: {proposed_plan_file}")
            logger.info(f"parent_execution_id: {parent_execution_id}")
            logger.info(f"status: {status}")
            
            execution = ExecutionModel(
                execution_id=execution_id,
                epic_key=epic_key,
                execution_plan_file=execution_plan_file,
                proposed_plan_file=proposed_plan_file,
                status=status,
                parent_execution_id=parent_execution_id
            )
            
            result = await self.executions.create_execution(execution)
            
            return ExecutionRecord(
                execution_id=result.execution_id,
                epic_key=result.epic_key,
                execution_plan_file=result.execution_plan_file,
                proposed_plan_file=result.proposed_plan_file,
                status=result.status,
                created_at=result.created_at,
                parent_execution_id=result.parent_execution_id
            )
            
        except Exception as e:
            logger.error(f"Failed to create execution record: {str(e)}")
            logger.error(f"Epic key: {epic_key}")
            logger.error(f"Execution ID: {execution_id}")
            raise
    
    async def create_revision_record(
        self,
        revision_id: str,
        execution_id: str,
        changes_requested: str,
        changes_interpreted: str,
        proposed_plan_file: str,
        execution_plan_file: str
    ) -> RevisionRecord:
        """Create a new revision record"""
        try:
            revision = RevisionModel(
                revision_id=revision_id,
                execution_id=execution_id,
                changes_requested=changes_requested,
                changes_interpreted=changes_interpreted,
                proposed_plan_file=proposed_plan_file,
                execution_plan_file=execution_plan_file
            )
            
            result = await self.revisions.insert_revision(revision)
            
            return RevisionRecord(
                revision_id=result.revision_id,
                execution_id=result.execution_id,
                proposed_plan_file=result.proposed_plan_file,
                execution_plan_file=result.execution_plan_file,
                status=result.status,
                created_at=result.created_at,
                changes_requested=result.changes_requested,
                changes_interpreted=result.changes_interpreted,
                accepted=result.accepted,
                accepted_at=result.accepted_at
            )
            
        except Exception as e:
            logger.error(f"Failed to create revision record: {str(e)}")
            raise
    
    async def get_execution_record(self, execution_id: str) -> ExecutionRecord:
        """Get execution record by ID"""
        result = await self.executions.get_execution(execution_id)
        if not result:
            raise ValueError(f"No execution found for ID: {execution_id}")
            
        return ExecutionRecord(
            execution_id=result.execution_id,
            epic_key=result.epic_key,
            execution_plan_file=result.execution_plan_file,
            proposed_plan_file=result.proposed_plan_file,
            status=result.status,
            created_at=result.created_at,
            parent_execution_id=result.parent_execution_id
        )
    
    async def get_revision_record(self, revision_id: str) -> RevisionRecord:
        """Get revision record by ID"""
        result = await self.revisions.get_revision(revision_id)
        if not result:
            raise ValueError(f"No revision found for ID: {revision_id}")
            
        return RevisionRecord(
            revision_id=result.revision_id,
            execution_id=result.execution_id,
            proposed_plan_file=result.proposed_plan_file,
            execution_plan_file=result.execution_plan_file,
            status=result.status,
            created_at=result.created_at,
            changes_requested=result.changes_requested,
            changes_interpreted=result.changes_interpreted,
            accepted=result.accepted,
            accepted_at=result.accepted_at
        )
    
    async def update_revision_status(
        self,
        revision_id: str,
        status: str
    ) -> None:
        """Update the status of a revision"""
        await self.revisions.update_revision_status(revision_id, status)
    
    async def get_revision_history(
        self,
        execution_id: str
    ) -> List[RevisionRecord]:
        """Get all revisions for an execution"""
        results = await self.revisions.get_revision_history(execution_id)
        
        return [
            RevisionRecord(
                revision_id=rev.revision_id,
                execution_id=rev.execution_id,
                proposed_plan_file=rev.proposed_plan_file,
                execution_plan_file=rev.execution_plan_file,
                status=rev.status,
                created_at=rev.created_at,
                changes_requested=rev.changes_requested,
                changes_interpreted=rev.changes_interpreted,
                accepted=rev.accepted,
                accepted_at=rev.accepted_at
            )
            for rev in results
        ]
    
    async def update_execution_status(
        self,
        execution_id: str,
        status: str
    ) -> ExecutionRecord:
        """Update the status of an execution record"""
        try:
            logger.info(f"Updating execution status to {status} for ID {execution_id}")
            
            result = await self.executions.update_execution_status(execution_id, status)
            if not result:
                raise ValueError(f"No execution found with ID: {execution_id}")
                
            return ExecutionRecord(
                execution_id=result.execution_id,
                epic_key=result.epic_key,
                execution_plan_file=result.execution_plan_file,
                proposed_plan_file=result.proposed_plan_file,
                status=result.status,
                created_at=result.created_at,
                parent_execution_id=result.parent_execution_id
            )
            
        except Exception as e:
            logger.error(f"Failed to update execution status: {str(e)}")
            logger.error(f"Execution ID: {execution_id}")
            logger.error(f"New status: {status}")
            raise 