import json
from datetime import datetime, UTC
from typing import Optional

from loguru import logger

from models.revision_record import RevisionRecord
from services.execution_log_service import ExecutionLogService
from services.mongodb_service import MongoDBService
from ..models import DateTimeEncoder


class StatusManager:
    """Manager for handling revision status updates"""

    def __init__(self):
        """Initialize the status manager"""
        self.mongodb = MongoDBService()
        self.execution_log = None

    def _ensure_execution_log(self, epic_key: str):
        """Ensure execution log is initialized with the correct epic key"""
        if not self.execution_log or self.execution_log.epic_key != epic_key:
            self.execution_log = ExecutionLogService(epic_key)

    async def update_revision_status(
            self,
            revision_id: str,
            status: str,
            accepted: Optional[bool] = None
    ) -> None:
        """Update the status of a revision"""
        try:
            # Get the revision to get the epic_key
            revision = self.mongodb.get_revision(revision_id)
            if not revision:
                raise ValueError(f"Revision {revision_id} not found")

            # Initialize execution log with the epic key from the revision (access as attribute)
            self._ensure_execution_log(revision.epic_key)

            # Update in MongoDB
            updated = self.mongodb.update_revision_status(revision_id, status, accepted)
            if not updated:
                raise ValueError(f"Failed to update revision {revision_id}")

            # Log the status update
            self.execution_log.log_section(
                "Revision Status Update",
                json.dumps({
                    "revision_id": revision_id,
                    "status": status,
                    "accepted": accepted,
                    "updated_at": datetime.now(UTC)
                }, indent=2, cls=DateTimeEncoder)
            )

        except Exception as e:
            logger.error(f"Failed to update revision status: {str(e)}")
            raise
