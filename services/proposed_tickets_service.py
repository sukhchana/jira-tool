from datetime import datetime
import os
import yaml
from typing import Dict, Any, List, Optional
from loguru import logger
import json
from uuid_extensions import uuid7
from database.mongodb_handlers import ProposedTicketsHandler, ProposalCountersHandler
from models.mongodb_models import ProposedTicketModel, ProposalCounterModel

class ProposedTicketsService:
    """Service for tracking proposed JIRA tickets"""
    
    def __init__(self):
        """Initialize the service with MongoDB handlers"""
        self.tickets = ProposedTicketsHandler()
        self.counters = ProposalCountersHandler()
        # Initialize ID counters
        self.id_counters = {
            "USER-STORY": 0,
            "TECHNICAL-TASK": 0,
            "SUB-TASK": 0,
            "SCENARIO": 0
        }
        logger.info("Initialized ProposedTicketsService with MongoDB")

    def _generate_id(self, type_prefix: str) -> str:
        """Generate a sequential ID for a given type"""
        self.id_counters[type_prefix] += 1
        return f"{type_prefix}-{self.id_counters[type_prefix]}"
    
    async def add_high_level_task(
        self,
        task: Dict[str, Any],
        epic_key: str,
        proposal_id: str,
        execution_id: str
    ) -> str:
        """Add a high-level task (user story or technical task)"""
        # Determine task type and generate ID
        is_user_story = task["type"] == "User Story"
        type_prefix = "USER-STORY" if is_user_story else "TECHNICAL-TASK"
        task_id = self._generate_id(type_prefix)
        
        task_data = {
            "id": task_id,
            "type": task["type"],
            "name": task["name"],
            "description": task["description"],
            "technical_domain": task["technical_domain"],
            "complexity": task["complexity"],
            "dependencies": task["dependencies"],
            "business_value": task.get("business_value"),
            "implementation_notes": task.get("implementation_notes"),
            "parent_epic": epic_key
        }
        
        # Add scenarios for user stories with IDs
        if is_user_story and "scenarios" in task:
            task_data["scenarios"] = [
                {
                    "id": self._generate_id("SCENARIO"),
                    "name": scenario["name"],
                    "steps": scenario["steps"]
                }
                for scenario in task["scenarios"]
            ]
        
        # Create ticket in MongoDB
        ticket = ProposedTicketModel(
            proposal_id=proposal_id,
            execution_id=execution_id,
            epic_key=epic_key,
            task_id=task_id,
            task_type=type_prefix,
            task_details=task_data
        )
        
        await self.tickets.insert_proposed_ticket(ticket)
        return task_id

    async def store_proposal(
        self,
        execution_id: str,
        epic_key: str,
        high_level_tasks: List[Dict[str, Any]],
        parent_proposal_id: Optional[str] = None
    ) -> str:
        """Store a new proposal"""
        try:
            # Validate input
            if not high_level_tasks:
                logger.error("No high-level tasks provided to store_proposal")
                raise ValueError("No high-level tasks provided")

            # Validate task structure
            for task in high_level_tasks:
                required_fields = ["type", "name", "description", "technical_domain", "complexity", "dependencies"]
                missing_fields = [field for field in required_fields if field not in task]
                if missing_fields:
                    logger.error(f"Task is missing required fields: {missing_fields}")
                    logger.error(f"Task content: {task}")
                    raise ValueError(f"Task is missing required fields: {missing_fields}")

            # Reset counters for new proposal
            self.id_counters = {key: 0 for key in self.id_counters}
            
            # Generate new proposal ID
            proposal_id = str(uuid7())
            logger.info(f"=== Starting to store proposal {proposal_id} ===")
            logger.info(f"Number of high-level tasks to process: {len(high_level_tasks)}")
            logger.info("Task Overview:")
            for idx, task in enumerate(high_level_tasks, 1):
                logger.info(f"{idx}. {task.get('type', 'Unknown Type')} - {task.get('name', 'Unnamed')}")
            
            # Store each high-level task with its subtasks
            total_subtasks = 0
            for task_index, task in enumerate(high_level_tasks, 1):
                # Generate unique ID for the high-level task
                task_type = "USER-STORY" if task.get("type") == "user_story" else "TECHNICAL-TASK"
                task_id = self._generate_id(task_type)
                
                logger.info(f"Processing high-level task {task_index}/{len(high_level_tasks)}")
                logger.info(f"Task ID: {task_id}, Type: {task_type}, Name: {task.get('name', 'Unnamed')}")
                logger.debug(f"Task details: {task}")
                
                # Store high-level task
                high_level_ticket = ProposedTicketModel(
                    proposal_id=proposal_id,
                    execution_id=execution_id,
                    epic_key=epic_key,
                    task_id=task_id,
                    task_type=task_type,
                    task_details=task
                )
                await self.tickets.insert_proposed_ticket(high_level_ticket)
                logger.info(f"✓ Stored high-level task: {task_id}")
                
                # Process and store subtasks
                subtasks = task.get("subtasks", [])
                if not isinstance(subtasks, list):
                    logger.warning(f"Subtasks for task {task_id} is not a list. Type: {type(subtasks)}")
                    subtasks = []
                
                logger.info(f"Found {len(subtasks)} subtasks for {task_id}")
                
                for subtask_index, subtask in enumerate(subtasks, 1):
                    # Validate subtask structure
                    required_subtask_fields = ["title", "description", "acceptance_criteria"]
                    missing_fields = [field for field in required_subtask_fields if field not in subtask]
                    if missing_fields:
                        logger.warning(f"Subtask {subtask_index} missing fields: {missing_fields}")
                        logger.warning(f"Skipping invalid subtask: {subtask}")
                        continue

                    subtask_id = self._generate_id("SUB-TASK")
                    logger.info(f"Processing subtask {subtask_index}/{len(subtasks)}")
                    logger.info(f"Subtask ID: {subtask_id}, Title: {subtask.get('title', 'Unnamed')}")
                    
                    subtask_ticket = ProposedTicketModel(
                        proposal_id=proposal_id,
                        execution_id=execution_id,
                        epic_key=epic_key,
                        task_id=subtask_id,
                        task_type="SUB-TASK",
                        parent_task_id=task_id,
                        task_details=subtask
                    )
                    await self.tickets.insert_proposed_ticket(subtask_ticket)
                    logger.info(f"✓ Stored subtask: {subtask_id}")
                    total_subtasks += 1
            
            # Store counter state
            counter = ProposalCounterModel(
                proposal_id=proposal_id,
                counter_data=self.id_counters
            )
            await self.counters.insert_proposal_counter(counter)
            
            logger.info("=== Proposal Storage Summary ===")
            logger.info(f"Proposal ID: {proposal_id}")
            logger.info(f"High-level tasks stored: {len(high_level_tasks)}")
            logger.info(f"Subtasks stored: {total_subtasks}")
            logger.info(f"Total tickets created: {len(high_level_tasks) + total_subtasks}")
            logger.info(f"Counter state: {self.id_counters}")
            
            return proposal_id
            
        except Exception as e:
            logger.error(f"Failed to store proposal: {str(e)}")
            logger.error(f"Current task being processed: {task_id if 'task_id' in locals() else 'No task ID'}")
            logger.error(f"Current subtask being processed: {subtask_id if 'subtask_id' in locals() else 'No subtask ID'}")
            if 'task' in locals():
                logger.error(f"Task that failed: {task}")
            raise

    async def get_proposal(self, proposal_id: str) -> List[Dict[str, Any]]:
        """Get a proposal's tasks by ID"""
        try:
            # Get all tickets for this proposal
            tickets = await self.tickets.get_proposal_tickets(proposal_id)
            
            # Organize into high-level tasks with subtasks
            high_level_tasks = {}
            subtasks = []
            
            for ticket in tickets:
                if not ticket.parent_task_id:
                    high_level_tasks[ticket.task_id] = {
                        **ticket.task_details,
                        "subtasks": []
                    }
                else:
                    subtasks.append(ticket)
            
            # Add subtasks to their parent tasks
            for subtask in subtasks:
                if subtask.parent_task_id in high_level_tasks:
                    high_level_tasks[subtask.parent_task_id]["subtasks"].append(
                        subtask.task_details
                    )
            
            return list(high_level_tasks.values())
                
        except Exception as e:
            logger.error(f"Failed to get proposal {proposal_id}: {str(e)}")
            raise

    async def get_proposal_by_execution(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get the latest proposal for an execution"""
        try:
            # Get all tickets for this execution
            tickets = await self.tickets.get_execution_tickets(execution_id)
            
            if not tickets:
                return []
            
            # Get the latest proposal_id
            proposal_id = tickets[0].proposal_id
            return await self.get_proposal(proposal_id)
                
        except Exception as e:
            logger.error(f"Failed to get proposal for execution {execution_id}: {str(e)}")
            raise

    async def export_proposal_to_yaml(
        self,
        proposal_id: str,
        output_path: Optional[str] = None
    ) -> str:
        """Export a proposal to YAML format"""
        try:
            # Get all tickets for this proposal
            tickets = await self.tickets.get_proposal_tickets(proposal_id)
            
            if not tickets:
                logger.error(f"No proposal found with ID: {proposal_id}")
                raise ValueError(f"No proposal found with ID: {proposal_id}")
            
            # Get proposal metadata from first ticket
            first_ticket = tickets[0]
            
            # Build YAML structure
            yaml_data = {
                "proposal_id": proposal_id,
                "execution_id": first_ticket.execution_id,
                "epic_key": first_ticket.epic_key,
                "created_at": first_ticket.created_at.isoformat(),
                "tasks": await self.get_proposal(proposal_id)
            }
            
            # Generate filename if not provided
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"proposed_tickets/PROPOSED_{first_ticket.epic_key}_{timestamp}.yaml"
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write YAML file
            with open(output_path, 'w') as f:
                yaml.safe_dump(
                    yaml_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )
            
            logger.info(f"Exported proposal {proposal_id} to {output_path}")
            return output_path
                
        except Exception as e:
            logger.error(f"Failed to export proposal {proposal_id}: {str(e)}")
            raise 