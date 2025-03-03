import os
from typing import Optional

from dotenv import load_dotenv
from loguru import logger
from pymongo import MongoClient
from pymongo.database import Database

# Load environment variables
load_dotenv()


class MongoConnection:
    """Singleton class for managing MongoDB connection"""

    _instance: Optional['MongoConnection'] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    def __new__(cls) -> 'MongoConnection':
        """Ensure only one instance of MongoConnection exists"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize MongoDB connection if not already initialized"""
        if MongoConnection._client is None:
            self._initialize_connection()

    def _initialize_connection(self):
        """Initialize the MongoDB connection"""
        try:
            connection_string = os.getenv("MONGO_CONNECTION_STRING")
            if not connection_string:
                raise ValueError("MONGO_CONNECTION_STRING environment variable is not set")

            MongoConnection._client = MongoClient(connection_string)
            MongoConnection._db = MongoConnection._client.jira_tool

            # Test connection
            MongoConnection._client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")

        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {str(e)}")
            raise

    @property
    def client(self) -> MongoClient:
        """Get the MongoDB client instance"""
        return MongoConnection._client

    @property
    def db(self) -> Database:
        """Get the database instance"""
        return MongoConnection._db

    def close(self):
        """Close the MongoDB connection"""
        if MongoConnection._client:
            MongoConnection._client.close()
            MongoConnection._client = None
            MongoConnection._db = None
            logger.info("MongoDB connection closed")
