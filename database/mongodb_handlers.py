from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from config.mongodb import MongoDBConnection
from models.mongodb_models import (
    ExecutionModel,
    RevisionModel,
    ProposedTicketModel,
    ProposalCounterModel
)

class BaseHandler:
    """Base handler with shared MongoDB connection logic"""
    _db_instance = None
    
    def __init__(self, collection_name: str):
        if not BaseHandler._db_instance:
            BaseHandler._db_instance = MongoDBConnection()
        self.db = BaseHandler._db_instance
        self._collection_name = collection_name
        self._collection = None
        
    @property
    async def collection(self):
        """Get the collection, ensuring connection is established"""
        if self._collection is None:
            if not self.db._client:
                await self.db.connect()
            self._collection = getattr(self.db, self._collection_name)
        return self._collection

class ExecutionsHandler(BaseHandler):
    """Handler for executions collection operations"""
    
    def __init__(self):
        super().__init__("executions")

    async def create_execution(self, execution: ExecutionModel) -> ExecutionModel:
        """Create a new execution record"""
        try:
            coll = await self.collection
            await coll.insert_one(execution.model_dump())
            return execution
        except Exception as e:
            logger.error(f"Failed to create execution record: {str(e)}")
            raise

    async def get_execution(self, execution_id: str) -> Optional[ExecutionModel]:
        """Get execution by ID"""
        try:
            coll = await self.collection
            # Use projection to only fetch needed fields
            doc = await coll.find_one(
                {"execution_id": execution_id},
                projection={"_id": 0}
            )
            return ExecutionModel(**doc) if doc else None
        except Exception as e:
            logger.error(f"Failed to get execution {execution_id}: {str(e)}")
            raise

    async def update_execution_status(self, execution_id: str, status: str) -> Optional[ExecutionModel]:
        """Update execution status"""
        try:
            coll = await self.collection
            result = await coll.find_one_and_update(
                {"execution_id": execution_id},
                {"$set": {"status": status}},
                return_document=True,
                projection={"_id": 0}
            )
            return ExecutionModel(**result) if result else None
        except Exception as e:
            logger.error(f"Failed to update execution status: {str(e)}")
            raise

class RevisionsHandler(BaseHandler):
    """Handler for revisions collection operations"""
    
    def __init__(self):
        super().__init__("revisions")

    async def insert_revision(self, revision: RevisionModel) -> RevisionModel:
        """Create a new revision record"""
        try:
            coll = await self.collection
            await coll.insert_one(revision.model_dump())
            return revision
        except Exception as e:
            logger.error(f"Failed to create revision record: {str(e)}")
            raise

    async def get_revision(self, revision_id: str) -> Optional[RevisionModel]:
        """Get revision by ID"""
        try:
            coll = await self.collection
            doc = await coll.find_one(
                {"revision_id": revision_id},
                projection={"_id": 0}
            )
            return RevisionModel(**doc) if doc else None
        except Exception as e:
            logger.error(f"Failed to get revision {revision_id}: {str(e)}")
            raise

    async def update_revision_status(
        self,
        revision_id: str,
        status: str,
        accepted: Optional[bool] = None
    ) -> Optional[RevisionModel]:
        """Update revision status"""
        try:
            update = {"status": status}
            if accepted is not None:
                update.update({
                    "accepted": accepted,
                    "accepted_at": datetime.now().isoformat() if accepted else None
                })

            coll = await self.collection
            result = await coll.find_one_and_update(
                {"revision_id": revision_id},
                {"$set": update},
                return_document=True,
                projection={"_id": 0}
            )
            return RevisionModel(**result) if result else None
        except Exception as e:
            logger.error(f"Failed to update revision status: {str(e)}")
            raise

    async def get_revision_history(self, execution_id: str) -> List[RevisionModel]:
        """Get revision history for an execution"""
        try:
            coll = await self.collection
            cursor = coll.find(
                {"execution_id": execution_id},
                projection={"_id": 0}
            ).sort("created_at", 1)
            
            return [RevisionModel(**doc) async for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get revision history: {str(e)}")
            raise

class ProposedTicketsHandler(BaseHandler):
    """Handler for proposed tickets collection operations"""
    
    def __init__(self):
        super().__init__("proposed_tickets")

    async def insert_proposed_ticket(self, ticket: ProposedTicketModel) -> ProposedTicketModel:
        """Create a new proposed ticket"""
        try:
            coll = await self.collection
            await coll.insert_one(ticket.model_dump())
            return ticket
        except Exception as e:
            logger.error(f"Failed to create proposed ticket: {str(e)}")
            raise

    async def insert_proposed_tickets_bulk(self, tickets: List[ProposedTicketModel]) -> List[ProposedTicketModel]:
        """Create multiple tickets in bulk"""
        try:
            if not tickets:
                return []
                
            coll = await self.collection
            operations = [ticket.model_dump() for ticket in tickets]
            await coll.insert_many(operations)
            return tickets
        except Exception as e:
            logger.error(f"Failed to create tickets in bulk: {str(e)}")
            raise

    async def get_proposal_tickets(self, proposal_id: str) -> List[ProposedTicketModel]:
        """Get all tickets for a proposal"""
        try:
            coll = await self.collection
            cursor = coll.find(
                {"proposal_id": proposal_id},
                projection={"_id": 0}
            )
            return [ProposedTicketModel(**doc) async for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get proposal tickets: {str(e)}")
            raise

    async def get_execution_tickets(self, execution_id: str) -> List[ProposedTicketModel]:
        """Get all tickets for an execution"""
        try:
            coll = await self.collection
            cursor = coll.find(
                {"execution_id": execution_id},
                projection={"_id": 0}
            )
            return [ProposedTicketModel(**doc) async for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get execution tickets: {str(e)}")
            raise

class ProposalCountersHandler(BaseHandler):
    """Handler for proposal counters collection operations"""
    
    def __init__(self):
        super().__init__("proposal_counters")

    async def insert_proposal_counter(self, counter: ProposalCounterModel) -> ProposalCounterModel:
        """Create a new proposal counter"""
        try:
            coll = await self.collection
            await coll.insert_one(counter.model_dump())
            return counter
        except Exception as e:
            logger.error(f"Failed to create proposal counter: {str(e)}")
            raise

    async def get_proposal_counter(self, proposal_id: str) -> Optional[ProposalCounterModel]:
        """Get counter by proposal ID"""
        try:
            coll = await self.collection
            doc = await coll.find_one(
                {"proposal_id": proposal_id},
                projection={"_id": 0}
            )
            return ProposalCounterModel(**doc) if doc else None
        except Exception as e:
            logger.error(f"Failed to get proposal counter: {str(e)}")
            raise

    async def update_proposal_counter(self, proposal_id: str, counter_data: Dict[str, int]) -> Optional[ProposalCounterModel]:
        """Update counter data"""
        try:
            coll = await self.collection
            result = await coll.find_one_and_update(
                {"proposal_id": proposal_id},
                {"$set": {"counter_data": counter_data}},
                return_document=True,
                projection={"_id": 0}
            )
            return ProposalCounterModel(**result) if result else None
        except Exception as e:
            logger.error(f"Failed to update proposal counter: {str(e)}")
            raise 