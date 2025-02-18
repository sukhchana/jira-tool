from typing import Dict, Any, Optional
from loguru import logger
from jira import JIRA
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BaseJiraOperation:
    """Base class for JIRA operations with common functionality"""
    
    def __init__(self):
        """Initialize JIRA client"""
        self.jira = self._initialize_jira()
    
    def _initialize_jira(self) -> JIRA:
        """Initialize JIRA client with credentials"""
        try:
            jira_url = os.getenv("JIRA_SERVER")
            jira_user = os.getenv("JIRA_EMAIL")
            jira_token = os.getenv("JIRA_API_TOKEN")
            
            if not all([jira_url, jira_user, jira_token]):
                raise ValueError(
                    "Missing required JIRA environment variables. "
                    "Please ensure JIRA_SERVER, JIRA_EMAIL, and JIRA_API_TOKEN are set."
                )
            
            return JIRA(
                server=jira_url,
                basic_auth=(jira_user, jira_token)
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize JIRA client: {str(e)}")
            raise
    
    def _get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get a JIRA issue by key"""
        try:
            issue = self.jira.issue(issue_key)
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "status": issue.fields.status.name,
                "issue_type": issue.fields.issuetype.name,
                "project": issue.fields.project.key
            }
        except Exception as e:
            logger.error(f"Failed to get JIRA issue {issue_key}: {str(e)}")
            return None
    
    def _create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str,
        parent_key: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a JIRA issue"""
        try:
            # Prepare issue fields
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type}
            }
            
            # Add parent link if provided
            if parent_key:
                if issue_type == 'Sub-task':
                    issue_dict['parent'] = {'key': parent_key}
                else:
                    # For stories/tasks, use Epic link
                    issue_dict['customfield_10014'] = parent_key
            
            # Add any additional fields
            if additional_fields:
                issue_dict.update(additional_fields)
            
            # Create the issue
            issue = self.jira.create_issue(fields=issue_dict)
            
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "issue_type": issue.fields.issuetype.name
            }
            
        except Exception as e:
            logger.error(f"Failed to create JIRA issue: {str(e)}")
            logger.error(f"Issue details: {issue_dict}")
            raise
    
    def _update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any]
    ) -> bool:
        """Update a JIRA issue"""
        try:
            issue = self.jira.issue(issue_key)
            issue.update(fields=fields)
            return True
        except Exception as e:
            logger.error(f"Failed to update JIRA issue {issue_key}: {str(e)}")
            logger.error(f"Update fields: {fields}")
            return False
    
    def _transition_issue(
        self,
        issue_key: str,
        transition_name: str
    ) -> bool:
        """Transition a JIRA issue to a new status"""
        try:
            issue = self.jira.issue(issue_key)
            transitions = self.jira.transitions(issue)
            
            # Find the transition ID
            transition_id = None
            for t in transitions:
                if t['name'].lower() == transition_name.lower():
                    transition_id = t['id']
                    break
            
            if not transition_id:
                raise ValueError(f"Transition '{transition_name}' not found")
            
            # Perform the transition
            self.jira.transition_issue(issue, transition_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to transition JIRA issue {issue_key}: {str(e)}")
            return False 