from typing import Dict, Any, List, Optional

from loguru import logger

from .base_operation import BaseJiraOperation


class TicketOperations(BaseJiraOperation):
    """Operations for managing JIRA tickets (stories, tasks, subtasks)"""

    async def create_story(
            self,
            project_key: str,
            summary: str,
            description: str,
            epic_key: Optional[str] = None,
            additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a user story"""
        try:
            return self._create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type="Story",
                parent_key=epic_key,
                additional_fields=additional_fields
            )
        except Exception as e:
            logger.error(f"Failed to create story: {str(e)}")
            raise

    async def create_task(
            self,
            project_key: str,
            summary: str,
            description: str,
            epic_key: Optional[str] = None,
            additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a technical task"""
        try:
            return self._create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type="Task",
                parent_key=epic_key,
                additional_fields=additional_fields
            )
        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}")
            raise

    async def create_subtask(
            self,
            project_key: str,
            summary: str,
            description: str,
            parent_key: str,
            additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a subtask"""
        try:
            return self._create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type="Sub-task",
                parent_key=parent_key,
                additional_fields=additional_fields
            )
        except Exception as e:
            logger.error(f"Failed to create subtask: {str(e)}")
            raise

    async def update_ticket(
            self,
            ticket_key: str,
            fields: Dict[str, Any]
    ) -> bool:
        """Update a ticket's fields"""
        try:
            return self._update_issue(ticket_key, fields)
        except Exception as e:
            logger.error(f"Failed to update ticket: {str(e)}")
            return False

    async def update_ticket_status(
            self,
            ticket_key: str,
            status: str
    ) -> bool:
        """Update a ticket's status"""
        try:
            return self._transition_issue(ticket_key, status)
        except Exception as e:
            logger.error(f"Failed to update ticket status: {str(e)}")
            return False

    async def get_ticket_details(
            self,
            ticket_key: str,
            include_subtasks: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a ticket"""
        try:
            logger.debug(f"Fetching ticket details for {ticket_key}")
            ticket = self._get_issue(ticket_key)

            if not ticket:
                logger.error(f"No ticket found with key {ticket_key}")
                return None

            if not isinstance(ticket, dict):
                logger.error(f"Unexpected ticket data type: {type(ticket)}")
                return None

            # Get issue type from the new structure
            issue_type = ticket.get("issuetype", {}).get("name")
            if not issue_type:
                logger.error(f"Could not determine issue type for ticket {ticket_key}")
                return None

            logger.debug(f"Ticket {ticket_key} is of type {issue_type}")

            if include_subtasks and issue_type in ["Story", "Task"]:
                logger.info(f"Fetching subtasks for {ticket_key}")
                # Get subtasks
                try:
                    jql = f'parent = {ticket_key} ORDER BY created ASC'
                    logger.debug(f"Subtask JQL query: {jql}")
                    subtasks = self.jira.search_issues(jql)
                    logger.info(f"Found {len(subtasks)} subtasks")

                    # Process subtasks with the new structure
                    ticket["subtasks"] = [
                        {
                            "key": subtask.key,
                            "summary": subtask.fields.summary,
                            "status": {
                                "name": subtask.fields.status.name if hasattr(subtask.fields.status,
                                                                              'name') else "Unknown"
                            }
                        }
                        for subtask in subtasks
                    ]
                except Exception as e:
                    logger.error(f"Failed to fetch subtasks: {str(e)}")
                    ticket["subtasks"] = []

            logger.debug(f"Final ticket data structure: {ticket}")
            return ticket

        except Exception as e:
            logger.error(f"Failed to get ticket details for {ticket_key}: {str(e)}")
            logger.exception("Full traceback:")
            return None

    async def get_linked_tickets(
            self,
            ticket_key: str,
            link_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get tickets linked to the specified ticket"""
        try:
            issue = self.jira.issue(ticket_key)
            linked_tickets = []

            for link in issue.fields.issuelinks:
                if hasattr(link, "outwardIssue"):
                    linked_issue = link.outwardIssue
                    link_name = link.type.outward
                elif hasattr(link, "inwardIssue"):
                    linked_issue = link.inwardIssue
                    link_name = link.type.inward
                else:
                    continue

                if link_type and link_name.lower() != link_type.lower():
                    continue

                linked_tickets.append({
                    "key": linked_issue.key,
                    "link_type": link_name,
                    "summary": linked_issue.fields.summary,
                    "status": linked_issue.fields.status.name,
                    "issue_type": linked_issue.fields.issuetype.name
                })

            return linked_tickets

        except Exception as e:
            logger.error(f"Failed to get linked tickets for {ticket_key}: {str(e)}")
            return []
