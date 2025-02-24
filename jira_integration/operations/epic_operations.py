from typing import Dict, Any, Optional

from loguru import logger

from .base_operation import BaseJiraOperation


class EpicOperations(BaseJiraOperation):
    """Operations for managing JIRA epics"""

    async def get_epic_details(self, epic_key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an epic"""
        try:
            logger.info(f"Fetching epic details from JIRA for {epic_key}")

            # Verify JIRA connection
            if not self.jira:
                logger.error("JIRA client is not initialized")
                return None

            logger.debug("Attempting to get issue from JIRA")
            epic = self._get_issue(epic_key)

            if not epic:
                logger.error(f"Could not find issue {epic_key} in JIRA")
                return None

            if not isinstance(epic, dict):
                logger.error(f"Unexpected epic data type: {type(epic)}")
                return None

            # Check issue type using the new structure
            issue_type = epic.get("issuetype", {}).get("name")
            logger.debug(f"Issue type for {epic_key}: {issue_type}")

            if not issue_type or issue_type != "Epic":
                logger.error(f"Issue {epic_key} is not an epic (type: {issue_type})")
                raise ValueError(f"Issue {epic_key} is not an epic")

            # Get all issues linked to this epic
            logger.info(f"Fetching linked issues for epic {epic_key}")
            jql = f'cf[10014] = {epic_key} ORDER BY created DESC'
            logger.debug(f"JQL query: {jql}")

            try:
                linked_issues = self.jira.search_issues(jql)
                logger.info(f"Found {len(linked_issues)} linked issues")
            except Exception as e:
                logger.error(f"Failed to fetch linked issues: {str(e)}")
                linked_issues = []

            # Organize linked issues by type
            stories = []
            tasks = []
            subtasks = []

            for issue in linked_issues:
                try:
                    issue_type = issue.fields.issuetype.name
                    issue_data = {
                        "key": issue.key,
                        "summary": issue.fields.summary,
                        "status": {
                            "name": issue.fields.status.name if hasattr(issue.fields.status, 'name') else "Unknown"
                        }
                    }

                    if issue_type == "Story":
                        stories.append(issue_data)
                    elif issue_type == "Task":
                        tasks.append(issue_data)
                    elif issue_type == "Sub-task":
                        subtasks.append(issue_data)

                except Exception as e:
                    logger.error(f"Error processing linked issue {issue.key}: {str(e)}")
                    continue

            logger.debug(
                f"Processed linked issues - Stories: {len(stories)}, Tasks: {len(tasks)}, Subtasks: {len(subtasks)}")

            # Enhance epic details with linked issues
            epic.update({
                "stories": stories,
                "tasks": tasks,
                "subtasks": subtasks,
                "total_issues": len(linked_issues)
            })

            logger.info(f"Successfully retrieved epic details for {epic_key}")
            logger.debug(f"Final epic data structure: {epic}")

            return epic

        except Exception as e:
            logger.error(f"Failed to get epic details for {epic_key}: {str(e)}")
            logger.exception("Full traceback:")
            return None

    async def create_epic(
            self,
            project_key: str,
            summary: str,
            description: str,
            additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new epic"""
        try:
            return self._create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type="Epic",
                additional_fields=additional_fields
            )
        except Exception as e:
            logger.error(f"Failed to create epic: {str(e)}")
            raise

    async def update_epic_status(self, epic_key: str, status: str) -> bool:
        """Update the status of an epic"""
        try:
            return self._transition_issue(epic_key, status)
        except Exception as e:
            logger.error(f"Failed to update epic status: {str(e)}")
            return False

    async def get_epic_progress(self, epic_key: str) -> Dict[str, Any]:
        """Get progress statistics for an epic"""
        try:
            epic = await self.get_epic_details(epic_key)
            if not epic:
                raise ValueError(f"Epic {epic_key} not found")

            # Calculate statistics
            total_issues = epic["total_issues"]
            completed_issues = sum(
                1 for issues in [epic["stories"], epic["tasks"], epic["subtasks"]]
                for issue in issues
                if issue["status"]["name"].lower() in ["done", "completed", "closed"]
            )

            return {
                "total_issues": total_issues,
                "completed_issues": completed_issues,
                "completion_percentage": (completed_issues / total_issues * 100) if total_issues > 0 else 0,
                "stories_count": len(epic["stories"]),
                "tasks_count": len(epic["tasks"]),
                "subtasks_count": len(epic["subtasks"])
            }

        except Exception as e:
            logger.error(f"Failed to get epic progress for {epic_key}: {str(e)}")
            raise
