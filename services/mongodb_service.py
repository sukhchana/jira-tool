import os
import sys
from pathlib import Path
from datetime import datetime

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
            user_stories = yaml_data.get('user_stories', [])
            for story in user_stories:
                # Create and insert the user story
                story_doc = ProposedTicketMongo(
                    ticket_id=story['id'],
                    ticket_type='USER_STORY',
                    parent_id=story.get('parent_id'),
                    title=story['name'],
                    description=story['description'],
                    technical_domain=story.get('technical_domain'),
                    complexity=story.get('complexity'),
                    dependencies=story.get('dependencies', []),
                    business_value=story.get('business_value'),
                    implementation_notes=story.get('implementation_notes'),
                    scenarios=story.get('scenarios', []),
                    modern_approaches=story.get('modern_approaches'),
                    accessibility_requirements=story.get('accessibility_requirements'),
                    integration_points=story.get('integration_points'),
                    user_experience=story.get('user_experience', {}),
                    implementation_details=story.get('implementation_details', {}),
                    epic_key=epic_key,
                    execution_id=execution_id
                )
                result = self.proposed_tickets.insert_one(story_doc.dict())
                proposal_ids.append(str(story_doc.proposal_id))
                
                # Process subtasks if any
                subtasks = yaml_data.get('subtasks', {}).get(story['name'], [])
                for subtask in subtasks:
                    # Ensure acceptance criteria is a list
                    acceptance_criteria = subtask.get('acceptance_criteria', [])
                    if isinstance(acceptance_criteria, str):
                        acceptance_criteria = [acceptance_criteria]
                    
                    subtask_doc = ProposedTicketMongo(
                        ticket_id=subtask['id'],
                        ticket_type='SUB_TASK',
                        parent_id=story['id'],
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
                    result = self.proposed_tickets.insert_one(subtask_doc.dict())
                    proposal_ids.append(str(subtask_doc.proposal_id))
            
            # Process technical tasks
            technical_tasks = yaml_data.get('technical_tasks', [])
            for task in technical_tasks:
                # Create and insert the technical task
                task_doc = ProposedTicketMongo(
                    ticket_id=task['id'],
                    ticket_type='TECHNICAL_TASK',
                    parent_id=task.get('parent_id'),
                    title=task['name'],
                    description=task['description'],
                    technical_domain=task.get('technical_domain'),
                    complexity=task.get('complexity'),
                    dependencies=task.get('dependencies', []),
                    implementation_notes=task.get('implementation_notes'),
                    modern_practices=task.get('modern_practices'),
                    security_considerations=task.get('security_considerations'),
                    implementation_details=task.get('implementation_details', {}),
                    epic_key=epic_key,
                    execution_id=execution_id
                )
                result = self.proposed_tickets.insert_one(task_doc.dict())
                proposal_ids.append(str(task_doc.proposal_id))
                
                # Process subtasks if any
                subtasks = yaml_data.get('subtasks', {}).get(task['name'], [])
                for subtask in subtasks:
                    # Ensure acceptance criteria is a list
                    acceptance_criteria = subtask.get('acceptance_criteria', [])
                    if isinstance(acceptance_criteria, str):
                        acceptance_criteria = [acceptance_criteria]
                        
                    subtask_doc = ProposedTicketMongo(
                        ticket_id=subtask['id'],
                        ticket_type='SUB_TASK',
                        parent_id=task['id'],
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
                    result = self.proposed_tickets.insert_one(subtask_doc.dict())
                    proposal_ids.append(str(subtask_doc.proposal_id))
            
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
            "updated_at": datetime.now()
        }
        if accepted is not None:
            update_data["accepted"] = accepted
            update_data["accepted_at"] = datetime.now()
            
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
            update_data["updated_at"] = datetime.now()
            
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
                        "updated_at": datetime.now()
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
                "created_at": datetime.now()
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
                "created_at": datetime.now()
            }
            
            # Get subtasks for this task
            subtasks = yaml_data.get('subtasks', {}).get(task['title'], [])
            if subtasks:
                task_doc["subtasks"] = subtasks
            
            self.tasks_collection.insert_one(task_doc)

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
