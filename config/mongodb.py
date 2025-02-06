import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGO_CONNECTION_STR = os.getenv('MONGO_CONNECTION_STRING')
if not MONGO_CONNECTION_STR:
    raise ValueError("MONGO_CONNECTION_STRING environment variable is not set")

# Database and Collection Names
DATABASE_NAME = "jira_tool"
COLLECTIONS = {
    "executions": "executions",
    "revisions": "revisions",
    "proposed_tickets": "proposed_tickets",
    "proposal_counters": "proposal_counters"
}

class MongoDBConnection:
    _instance: Optional['MongoDBConnection'] = None
    _client: Optional[AsyncIOMotorClient] = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
        return cls._instance

    async def connect(self):
        """Initialize database connection"""
        if not self._client:
            try:
                self._client = AsyncIOMotorClient(MONGO_CONNECTION_STR)
                self._db = self._client[DATABASE_NAME]
                logger.info("Successfully connected to MongoDB")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {str(e)}")
                raise

    async def close(self):
        """Close database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Closed MongoDB connection")

    @property
    def db(self):
        """Get database instance"""
        if not self._client:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    @property
    def executions(self):
        """Get executions collection"""
        return self.db[COLLECTIONS["executions"]]

    @property
    def revisions(self):
        """Get revisions collection"""
        return self.db[COLLECTIONS["revisions"]]

    @property
    def proposed_tickets(self):
        """Get proposed tickets collection"""
        return self.db[COLLECTIONS["proposed_tickets"]]

    @property
    def proposal_counters(self):
        """Get proposal counters collection"""
        return self.db[COLLECTIONS["proposal_counters"]]

# Create indexes for collections
async def create_indexes():
    """Create necessary indexes for collections"""
    db = MongoDBConnection()
    await db.connect()

    # Executions indexes
    await db.executions.create_index("execution_id", unique=True)
    await db.executions.create_index("epic_key")
    await db.executions.create_index("created_at")

    # Revisions indexes
    await db.revisions.create_index("revision_id", unique=True)
    await db.revisions.create_index("execution_id")
    await db.revisions.create_index("created_at")

    # Proposed tickets indexes
    await db.proposed_tickets.create_index([("proposal_id", 1), ("task_id", 1)], unique=True)
    await db.proposed_tickets.create_index("execution_id")
    await db.proposed_tickets.create_index("created_at")

    # Proposal counters indexes
    await db.proposal_counters.create_index("proposal_id", unique=True)

    logger.info("Successfully created MongoDB indexes") 