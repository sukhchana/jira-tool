import os
import sys
from datetime import datetime, UTC
from pathlib import Path

# Add project root to Python path when running independently
if __name__ == "__main__":
    project_root = str(Path(__file__).parent.parent)
    sys.path.insert(0, project_root)

from typing import List, Optional, Dict, Any
from pymongo.collection import Collection
from models.proposed_ticket_mongo import ProposedTicketMongo
import yaml
from loguru import logger
from database import MongoConnection


class MongoDBService:
    """Service for handling MongoDB operations"""

    def __init__(self):
        """Initialize MongoDB collections using centralized connection"""
        # Get database instance from connection manager
        self.db = MongoConnection().db

        # Initialize collections
        self.proposed_tickets: Collection = self.db.proposed_tickets
        self.revisions: Collection = self.db.revisions
        self.executions: Collection = self.db.executions

        # Create indexes
        self._setup_indexes()

    def _setup_indexes(self):
        """Setup necessary indexes for the collections"""
        # Indexes for proposed_tickets collection
        self.proposed_tickets.create_index("proposal_id")
        self.proposed_tickets.create_index([("epic_key", 1), ("execution_id", 1)])
        self.proposed_tickets.create_index([("proposal_id", 1), ("parent_id", 1)])

        # Indexes for revisions collection
        self.revisions.create_index("revision_id", unique=True)
        self.revisions.create_index([("execution_id", 1), ("ticket_id", 1)])
        self.revisions.create_index("status")

        # Indexes for executions collection
        self.executions.create_index("execution_id", unique=True)
        self.executions.create_index("epic_key")
        self.executions.create_index("status")
        self.executions.create_index("parent_execution_id")

    def _process_subtasks(self, parent_id: str, subtasks: List[Dict], epic_key: str, execution_id: str) -> List[str]:
        """Helper method to process and persist subtasks
        
        Args:
            parent_id: ID of the parent ticket
            subtasks: List of subtask dictionaries
            epic_key: Epic key for the tickets
            execution_id: Execution ID for the tickets
            
        Returns:
            List of proposal IDs for the created subtasks
        """
        proposal_ids = []
        for subtask in subtasks:
            # Ensure acceptance criteria is a list
            acceptance_criteria = subtask.get('acceptance_criteria', [])
            if isinstance(acceptance_criteria, str):
                acceptance_criteria = [acceptance_criteria]

            subtask_doc = ProposedTicketMongo(
                ticket_id=subtask['id'],
                ticket_type='SUB_TASK',
                parent_id=parent_id,
                title=subtask['title'],
                description=subtask['description'],
                acceptance_criteria=acceptance_criteria,
                story_points=subtask.get('story_points'),
                required_skills=subtask.get('required_skills', []),
                suggested_assignee=subtask.get('suggested_assignee'),
                dependencies=subtask.get('dependencies', []),
                implementation_details=subtask.get('implementation_details', {}),
                epic_key=epic_key,
                execution_id=execution_id
            )
            result = self.proposed_tickets.insert_one(subtask_doc.model_dump())
            proposal_ids.append(str(subtask_doc.proposal_id))
        return proposal_ids

    def _process_high_level_ticket(self, ticket_data: Dict, ticket_type: str, epic_key: str, execution_id: str) -> \
    tuple[str, str]:
        """Helper method to process and persist main tickets (user stories or technical tasks)
        
        Args:
            ticket_data: Dictionary containing ticket data
            ticket_type: Type of ticket (USER_STORY or TECHNICAL_TASK)
            epic_key: Epic key for the ticket
            execution_id: Execution ID for the ticket
            
        Returns:
            Tuple of (ticket_id, proposal_id)
        """
        common_fields = {
            'ticket_id': ticket_data['id'],
            'ticket_type': ticket_type,
            'parent_id': ticket_data.get('parent_id'),
            'title': ticket_data['title'],
            'description': ticket_data['description'],
            'technical_domain': ticket_data.get('technical_domain'),
            'complexity': ticket_data.get('complexity'),
            'dependencies': ticket_data.get('dependencies', []),
            'implementation_notes': ticket_data.get('implementation_notes'),
            'implementation_details': ticket_data.get('implementation_details', {}),
            'epic_key': epic_key,
            'execution_id': execution_id
        }

        # Add type-specific fields
        if ticket_type == 'USER_STORY':
            additional_fields = {
                'business_value': ticket_data.get('business_value'),
                'scenarios': ticket_data.get('scenarios', []),
                'modern_approaches': ticket_data.get('modern_approaches'),
                'accessibility_requirements': ticket_data.get('accessibility_requirements'),
                'integration_points': ticket_data.get('integration_points'),
                'user_experience': ticket_data.get('user_experience', {})
            }
        else:  # TECHNICAL_TASK
            additional_fields = {
                'modern_practices': ticket_data.get('modern_practices'),
                'security_considerations': ticket_data.get('security_considerations')
            }

        # Combine fields and create document
        ticket_doc = ProposedTicketMongo(**{**common_fields, **additional_fields})
        result = self.proposed_tickets.insert_one(ticket_doc.model_dump())

        return ticket_data['id'], str(ticket_doc.proposal_id)

    def persist_proposed_tickets_from_yaml(self, yaml_file_path: str) -> List[str]:
        """
        Read proposed tickets from a YAML file and persist them to MongoDB
        Returns list of inserted proposal IDs
        """
        try:
            # Read YAML file
            with open(yaml_file_path, 'r') as f:
                yaml_data = yaml.safe_load(f)

            # Extract epic key and execution id from yaml data
            epic_key = yaml_data.get('epic_key')
            execution_id = yaml_data.get('execution_id')

            if not epic_key or not execution_id:
                raise ValueError("YAML file must contain epic_key and execution_id")

            proposal_ids = []

            # Process user stories
            for story in yaml_data.get('user_stories', []):
                story_id, proposal_id = self._process_high_level_ticket(story, 'USER_STORY', epic_key, execution_id)
                proposal_ids.append(proposal_id)

                # Process subtasks if any
                subtasks = yaml_data.get('subtasks', {}).get(story['title'], [])
                proposal_ids.extend(self._process_subtasks(story_id, subtasks, epic_key, execution_id))

            # Process technical tasks
            for task in yaml_data.get('technical_tasks', []):
                task_id, proposal_id = self._process_high_level_ticket(task, 'TECHNICAL_TASK', epic_key, execution_id)
                proposal_ids.append(proposal_id)

                # Process subtasks if any
                subtasks = yaml_data.get('subtasks', {}).get(task['title'], [])
                proposal_ids.extend(self._process_subtasks(task_id, subtasks, epic_key, execution_id))

            return proposal_ids

        except Exception as e:
            logger.error(f"Error persisting proposed tickets from YAML: {str(e)}")
            raise

    def get_tickets_by_proposal_id(self, proposal_id: str) -> List[ProposedTicketMongo]:
        """Get all tickets for a given proposal ID"""
        cursor = self.proposed_tickets.find({"proposal_id": proposal_id})
        return [ProposedTicketMongo(**doc) for doc in cursor]

    def get_tickets_by_epic_key(self, epic_key: str, execution_id: Optional[str] = None) -> List[ProposedTicketMongo]:
        """Get all tickets for a given epic key, optionally filtered by execution ID"""
        query = {"epic_key": epic_key}
        if execution_id:
            query["execution_id"] = execution_id

        cursor = self.proposed_tickets.find(query)
        return [ProposedTicketMongo(**doc) for doc in cursor]

    def get_tickets_by_parent_id(self, proposal_id: str, parent_id: str) -> List[ProposedTicketMongo]:
        """Get all subtasks for a given parent ticket within a proposal"""
        cursor = self.proposed_tickets.find({
            "proposal_id": proposal_id,
            "parent_id": parent_id
        })
        return [ProposedTicketMongo(**doc) for doc in cursor]

    def get_tickets_by_execution_id(self, execution_id: str) -> List[ProposedTicketMongo]:
        """Get all tickets for a given execution ID"""
        cursor = self.proposed_tickets.find({"execution_id": execution_id})
        return [ProposedTicketMongo(**doc) for doc in cursor]

    def get_ticket_by_execution_and_id(self, execution_id: str, ticket_id: str) -> Optional[ProposedTicketMongo]:
        """Get a specific ticket by execution ID and ticket ID"""
        doc = self.proposed_tickets.find_one({
            "execution_id": execution_id,
            "ticket_id": ticket_id
        })
        return ProposedTicketMongo(**doc) if doc else None

    def create_revision(self, revision: Dict[str, Any]) -> str:
        """Create a new revision record in MongoDB"""
        result = self.revisions.insert_one(revision)
        return str(result.inserted_id)

    def get_revision(self, revision_id: str) -> Optional[Dict[str, Any]]:
        """Get a revision record by ID"""
        return self.revisions.find_one({"revision_id": revision_id})

    def update_revision_status(self, revision_id: str, status: str, accepted: Optional[bool] = None) -> bool:
        """Update the status of a revision"""
        update_data = {
            "status": status,
            "updated_at": datetime.now(UTC)
        }
        if accepted is not None:
            update_data["accepted"] = accepted
            update_data["accepted_at"] = datetime.now(UTC)

        result = self.revisions.update_one(
            {"revision_id": revision_id},
            {"$set": update_data}
        )
        return result.modified_count > 0

    def get_revisions_by_execution_id(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get all revisions for a given execution"""
        return list(self.revisions.find({"execution_id": execution_id}))

    def update_ticket(self, execution_id: str, ticket_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a ticket in MongoDB"""
        try:
            # Add updated_at timestamp
            update_data["updated_at"] = datetime.now(UTC)

            result = self.proposed_tickets.update_one(
                {
                    "execution_id": execution_id,
                    "ticket_id": ticket_id
                },
                {"$set": update_data}
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Failed to update ticket: {str(e)}")
            logger.error(f"Execution ID: {execution_id}")
            logger.error(f"Ticket ID: {ticket_id}")
            logger.error(f"Update data: {update_data}")
            raise

    def create_execution(self, execution_record: Dict[str, Any]) -> str:
        """Create a new execution record in MongoDB
        
        Args:
            execution_record: Dictionary containing execution record data
            
        Returns:
            str: The execution_id of the created record
        """
        try:
            # Ensure required fields
            required_fields = ["execution_id", "epic_key", "execution_plan_file",
                               "proposed_plan_file", "status", "created_at"]
            for field in required_fields:
                if field not in execution_record:
                    raise ValueError(f"Missing required field: {field}")

            result = self.executions.insert_one(execution_record)
            logger.info(f"Created execution record: {execution_record['execution_id']}")
            return execution_record["execution_id"]

        except Exception as e:
            logger.error(f"Failed to create execution record: {str(e)}")
            raise

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get an execution record by ID"""
        return self.executions.find_one({"execution_id": execution_id})

    def get_executions_by_epic(self, epic_key: str) -> List[Dict[str, Any]]:
        """Get all execution records for a given epic"""
        return list(self.executions.find({"epic_key": epic_key}))

    def update_execution_status(self, execution_id: str, status: str) -> bool:
        """Update the status of an execution record
        
        Args:
            execution_id: The ID of the execution to update
            status: The new status value
            
        Returns:
            bool: True if update was successful
        """
        try:
            result = self.executions.update_one(
                {"execution_id": execution_id},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.now(UTC)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update execution status: {str(e)}")
            raise

    def save_user_stories(self, stories: List[Dict[str, Any]], yaml_data: Dict[str, Any]) -> None:
        """Save user stories to MongoDB"""
        for story in stories:
            story_doc = {
                "epic_key": self.epic_key,
                "execution_id": self.execution_id,
                "type": "User Story",
                "title": story['title'],
                "description": story.get('description', ''),
                "technical_domain": story.get('technical_domain', ''),
                "complexity": story.get('complexity', 'Medium'),
                "dependencies": story.get('dependencies', []),
                "implementation_details": story.get('implementation_details', {}),
                "created_at": datetime.now(UTC)
            }

            # Get subtasks for this story
            subtasks = yaml_data.get('subtasks', {}).get(story['title'], [])
            if subtasks:
                story_doc["subtasks"] = subtasks

            self.stories_collection.insert_one(story_doc)

    def save_technical_tasks(self, tasks: List[Dict[str, Any]], yaml_data: Dict[str, Any]) -> None:
        """Save technical tasks to MongoDB"""
        for task in tasks:
            task_doc = {
                "epic_key": self.epic_key,
                "execution_id": self.execution_id,
                "type": "Technical Task",
                "title": task['title'],
                "description": task.get('description', ''),
                "technical_domain": task.get('technical_domain', ''),
                "complexity": task.get('complexity', 'Medium'),
                "dependencies": task.get('dependencies', []),
                "implementation_details": task.get('implementation_details', {}),
                "created_at": datetime.now(UTC)
            }

            # Get subtasks for this task
            subtasks = yaml_data.get('subtasks', {}).get(task['title'], [])
            if subtasks:
                task_doc["subtasks"] = subtasks

            self.tasks_collection.insert_one(task_doc)

    def prepare_ticket_update(self, ticket_data: Any, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare update data for a ticket based on changes

        Args:
            ticket_data: Current ticket data
            changes: Dictionary containing changes to apply with keys:
                - field_updates: Direct field updates
                - list_append: Lists of values to append to fields
                - list_remove: Lists of values to remove from fields

        Returns:
            Dictionary containing the prepared update data
        """
        update_data = {}

        # Apply direct field updates
        update_data.update(changes.get("field_updates", {}))

        # Handle list append operations
        for field, values in changes.get("list_append", {}).items():
            current = ticket_data.model_dump().get(field, [])
            if not isinstance(current, list):
                current = []
            update_data[field] = list(set(current + values))

        # Handle list remove operations
        for field, values in changes.get("list_remove", {}).items():
            current = ticket_data.model_dump().get(field, [])
            if not isinstance(current, list):
                continue
            update_data[field] = [v for v in current if v not in values]

        return update_data


if __name__ == "__main__":
    try:
        logger.info("Starting MongoDB service test")
        service = MongoDBService()
        yaml_file = "proposed_tickets/PROPOSED_DP-7_20250207_140330.yaml"

        if not os.path.exists(yaml_file):
            logger.error(f"YAML file not found: {yaml_file}")
            sys.exit(1)

        logger.info(f"Processing YAML file: {yaml_file}")
        proposal_ids = service.persist_proposed_tickets_from_yaml(yaml_file)
        logger.info(f"Successfully persisted {len(proposal_ids)} tickets to MongoDB")
        logger.info(f"Proposal IDs: {proposal_ids}")

    except Exception as e:
        logger.error(f"Error running MongoDB service: {str(e)}")
        sys.exit(1)
