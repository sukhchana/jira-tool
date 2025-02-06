from typing import Dict, Any, List
from loguru import logger
from config.mongodb import MongoDBConnection
from models.mongodb_models import (
    ExecutionModel,
    RevisionModel,
    ProposedTicketModel,
    ProposalCounterModel
)

class ProposalNotFoundError(Exception):
    """Raised when a proposal is not found"""
    pass

class ExecutionNotFoundError(Exception):
    """Raised when an execution record is not found"""
    pass

class DebugService:
    """Service for debugging and inspecting database state"""
    
    def __init__(self):
        self.db = MongoDBConnection()

    async def list_executions(self) -> List[Dict[str, Any]]:
        """List all execution records"""
        try:
            cursor = self.db.executions.find().sort("created_at", -1)
            executions = []
            async for doc in cursor:
                executions.append(ExecutionModel(**doc).dict())
            return executions
                
        except Exception as e:
            logger.error(f"Failed to list executions: {str(e)}")
            raise

    async def list_revisions(self) -> List[Dict[str, Any]]:
        """List all revision records"""
        try:
            cursor = self.db.revisions.find().sort("created_at", -1)
            revisions = []
            async for doc in cursor:
                revisions.append(RevisionModel(**doc).dict())
            return revisions
                
        except Exception as e:
            logger.error(f"Failed to list revisions: {str(e)}")
            raise

    async def get_execution_details(self, execution_id: str) -> Dict[str, Any]:
        """Get execution record and its revision history"""
        try:
            # Get execution record
            execution_doc = await self.db.executions.find_one({"execution_id": execution_id})
            
            if not execution_doc:
                raise ExecutionNotFoundError(f"No execution found with ID: {execution_id}")
            
            # Get revision history
            cursor = self.db.revisions.find(
                {"execution_id": execution_id}
            ).sort("created_at", -1)
            
            revisions = []
            async for doc in cursor:
                revisions.append(RevisionModel(**doc).dict())
            
            return {
                "execution": ExecutionModel(**execution_doc).dict(),
                "revisions": revisions
            }
                
        except ExecutionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get execution details: {str(e)}")
            raise

    async def get_proposal_details(self, proposal_id: str) -> Dict[str, Any]:
        """Get proposal details by ID"""
        try:
            cursor = self.db.proposed_tickets.find({"proposal_id": proposal_id})
            tickets = []
            async for doc in cursor:
                tickets.append(ProposedTicketModel(**doc).dict())
            
            if not tickets:
                raise ProposalNotFoundError(f"No proposal found with ID: {proposal_id}")
                
            return {
                "proposal_id": proposal_id,
                "tickets": tickets
            }
            
        except ProposalNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get proposal details: {str(e)}")
            raise

    async def get_execution_proposals(self, execution_id: str) -> Dict[str, Any]:
        """Get all proposals for an execution"""
        try:
            # Check if execution exists
            execution_exists = await self.db.executions.count_documents(
                {"execution_id": execution_id}
            )
            
            if not execution_exists:
                raise ExecutionNotFoundError(f"No execution found with ID: {execution_id}")
            
            # Get proposals
            cursor = self.db.proposed_tickets.aggregate([
                {"$match": {"execution_id": execution_id}},
                {"$sort": {"created_at": -1}},
                {"$group": {
                    "_id": "$proposal_id",
                    "tickets": {"$push": "$$ROOT"},
                    "created_at": {"$first": "$created_at"}
                }},
                {"$sort": {"created_at": -1}}
            ])
            
            proposals = []
            async for group in cursor:
                proposal_id = group["_id"]
                tickets = [ProposedTicketModel(**doc).dict() for doc in group["tickets"]]
                proposals.append({
                    "proposal_id": proposal_id,
                    "tickets": tickets
                })
            
            return {
                "execution_id": execution_id,
                "proposals": proposals
            }
                
        except ExecutionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get execution proposals: {str(e)}")
            raise

    async def list_proposals(self) -> List[Dict[str, Any]]:
        """List all proposals"""
        try:
            cursor = self.db.proposed_tickets.aggregate([
                {"$sort": {"created_at": -1}},
                {"$group": {
                    "_id": "$proposal_id",
                    "execution_id": {"$first": "$execution_id"},
                    "created_at": {"$first": "$created_at"},
                    "tickets": {"$push": "$$ROOT"}
                }}
            ])
            
            proposals = []
            async for group in cursor:
                proposals.append({
                    "proposal_id": group["_id"],
                    "execution_id": group["execution_id"],
                    "created_at": group["created_at"],
                    "tickets": [
                        ProposedTicketModel(**doc).dict()
                        for doc in group["tickets"]
                    ]
                })
            
            return proposals
                
        except Exception as e:
            logger.error(f"Failed to list proposals: {str(e)}")
            raise 