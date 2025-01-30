from typing import Dict, Any, Optional, List
from uuid_extensions import uuid7
import sqlite3
from datetime import datetime
import os
from loguru import logger
from dataclasses import dataclass
from config.database import DATABASE
from pathlib import Path

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
        """Initialize the tracker service with SQLite database"""
        self.db_file = DATABASE["sqlite"]["path"]
        self.db_dir = Path(self.db_file).parent
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            # Create executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    epic_key TEXT NOT NULL,
                    execution_plan_file TEXT NOT NULL,
                    proposed_plan_file TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    parent_execution_id TEXT,
                    FOREIGN KEY (parent_execution_id) REFERENCES executions (execution_id)
                )
            """)
            
            # Create revisions table with execution_plan_file
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revisions (
                    revision_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    proposed_plan_file TEXT NOT NULL,
                    execution_plan_file TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    changes_requested TEXT NOT NULL,
                    changes_interpreted TEXT NOT NULL,
                    accepted BOOLEAN,
                    accepted_at TIMESTAMP,
                    FOREIGN KEY (execution_id) REFERENCES executions (execution_id)
                )
            """)
            
            conn.commit()
    
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
            logger.info(f"Creating execution record for epic {epic_key} with ID {execution_id}")
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO executions (
                        execution_id, epic_key, execution_plan_file,
                        proposed_plan_file, status, created_at,
                        parent_execution_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id,
                    epic_key,
                    execution_plan_file,
                    proposed_plan_file,
                    status,
                    datetime.now().isoformat(),
                    parent_execution_id if parent_execution_id else None
                ))
                conn.commit()
                
            record = await self.get_execution_record(execution_id)
            logger.info(f"Successfully created execution record for {epic_key}")
            return record
            
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
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO revisions (
                        revision_id, execution_id, proposed_plan_file,
                        execution_plan_file, status, created_at, 
                        changes_requested, changes_interpreted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    revision_id,
                    execution_id,
                    proposed_plan_file,
                    execution_plan_file,
                    "PENDING",
                    datetime.now().isoformat(),
                    changes_requested,
                    changes_interpreted
                ))
                conn.commit()
                
            return await self.get_revision_record(revision_id)
            
        except Exception as e:
            logger.error(f"Failed to create revision record: {str(e)}")
            raise
    
    async def get_execution_record(self, execution_id: str) -> ExecutionRecord:
        """Get execution record by ID"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM executions WHERE execution_id = ?",
                (execution_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"No execution found for ID: {execution_id}")
                
            return ExecutionRecord(
                execution_id=row[0],
                epic_key=row[1],
                execution_plan_file=row[2],
                proposed_plan_file=row[3],
                status=row[4],
                created_at=datetime.fromisoformat(row[5]),
                parent_execution_id=row[6] if row[6] else None
            )
    
    async def get_revision_record(self, revision_id: str) -> RevisionRecord:
        """Get revision record by ID"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM revisions WHERE revision_id = ?",
                (revision_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"No revision found for ID: {revision_id}")
                
            return RevisionRecord(
                revision_id=row[0],
                execution_id=row[1],
                proposed_plan_file=row[2],
                execution_plan_file=row[3],
                status=row[4],
                created_at=datetime.fromisoformat(row[5]),
                changes_requested=row[6],
                changes_interpreted=row[7],
                accepted=row[8],
                accepted_at=datetime.fromisoformat(row[9]) if row[9] else None
            )
    
    async def update_revision_status(
        self,
        revision_id: str,
        status: str
    ) -> None:
        """Update the status of a revision"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE revisions SET status = ? WHERE revision_id = ?",
                (status, revision_id)
            )
            conn.commit()
    
    async def get_revision_history(
        self,
        execution_id: str
    ) -> List[RevisionRecord]:
        """Get all revisions for an execution"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM revisions WHERE execution_id = ? ORDER BY created_at",
                (execution_id,)
            )
            rows = cursor.fetchall()
            
            return [
                RevisionRecord(
                    revision_id=row[0],
                    execution_id=row[1],
                    proposed_plan_file=row[2],
                    execution_plan_file=row[3],
                    status=row[4],
                    created_at=datetime.fromisoformat(row[5]),
                    changes_requested=row[6],
                    changes_interpreted=row[7],
                    accepted=row[8],
                    accepted_at=datetime.fromisoformat(row[9]) if row[9] else None
                )
                for row in rows
            ] 