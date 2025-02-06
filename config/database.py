import os
from pathlib import Path
import sqlite3
from loguru import logger

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Database settings
DATABASE = {
    "sqlite": {
        "filename": "execution_tracker.db",
        "directory": "data",
        "path": str(PROJECT_ROOT / "data" / "execution_tracker.db")
    }
}

SCHEMA = {
    "executions": """
        CREATE TABLE IF NOT EXISTS executions (
            execution_id TEXT PRIMARY KEY,
            epic_key TEXT NOT NULL,
            execution_plan_file TEXT NOT NULL,
            proposed_plan_file TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'NEW',
            parent_execution_id TEXT,
            FOREIGN KEY (parent_execution_id) REFERENCES executions(execution_id)
        )
    """,
    
    "revisions": """
        CREATE TABLE IF NOT EXISTS revisions (
            revision_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            changes_requested TEXT NOT NULL,
            changes_interpreted TEXT NOT NULL,
            proposed_plan_file TEXT NOT NULL,
            execution_plan_file TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            accepted BOOLEAN,
            accepted_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
        )
    """,
    
    "proposed_tickets": """
        CREATE TABLE IF NOT EXISTS proposed_tickets (
            proposal_id TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            epic_key TEXT NOT NULL,
            task_id TEXT NOT NULL,
            task_type TEXT NOT NULL CHECK(task_type IN ('USER-STORY', 'TECHNICAL-TASK', 'SUB-TASK')),
            parent_task_id TEXT,
            task_details TEXT NOT NULL,  -- JSON string containing all task data
            created_at TEXT NOT NULL,
            PRIMARY KEY (proposal_id, task_id),
            FOREIGN KEY (execution_id) REFERENCES executions(execution_id),
            FOREIGN KEY (proposal_id, parent_task_id) REFERENCES proposed_tickets(proposal_id, task_id),
            CHECK (
                (task_type IN ('USER-STORY', 'TECHNICAL-TASK') AND parent_task_id IS NULL) OR
                (task_type = 'SUB-TASK' AND parent_task_id IS NOT NULL)
            )
        )
    """,
    
    "proposal_counters": """
        CREATE TABLE IF NOT EXISTS proposal_counters (
            proposal_id TEXT PRIMARY KEY,
            counter_data TEXT NOT NULL,
            FOREIGN KEY (proposal_id) REFERENCES proposed_tickets(proposal_id)
        )
    """
}

def init_database():
    """Initialize database with schema"""
    try:
        db_path = DATABASE["sqlite"]["path"]
        
        # Remove existing database
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info("Removed existing database")
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
        # Create new database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create all tables
            for table_name, create_sql in SCHEMA.items():
                logger.info(f"Creating table: {table_name}")
                cursor.execute(create_sql)
            
            conn.commit()
            logger.info("Database initialization complete")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def check_database_state():
    """Check and log the current state of the database"""
    try:
        with sqlite3.connect(DATABASE["sqlite"]["path"]) as conn:
            cursor = conn.cursor()
            
            # List all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            if not tables:
                logger.warning("No tables found in database!")
                init_database()
                return
                
            logger.info("Existing tables:")
            for table in tables:
                logger.info(f"- {table[0]}")
                
    except Exception as e:
        logger.error(f"Failed to check database state: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Checking database state...")
    init_database()  # Just recreate it every time when run directly
    check_database_state()
    