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
            logger.info(f"Making JIRA API call to fetch issue: {issue_key}")
            
            # Verify JIRA connection
            if not hasattr(self, 'jira') or not self.jira:
                logger.error("JIRA client not properly initialized")
                return None
            
            try:
                issue = self.jira.issue(issue_key)
                logger.debug(f"Successfully retrieved issue from JIRA API")
                logger.debug(f"Issue type: {type(issue)}")
            except Exception as e:
                logger.error(f"JIRA API call failed: {str(e)}")
                return None
            
            # Extract basic issue data
            try:
                # Verify we have access to all required fields
                if not hasattr(issue, 'fields'):
                    logger.error("Issue object does not have 'fields' attribute")
                    logger.debug(f"Issue object attributes: {dir(issue)}")
                    return None
                
                if not hasattr(issue.fields, 'issuetype') or not hasattr(issue.fields.issuetype, 'name'):
                    logger.error("Issue type information is missing or incomplete")
                    return None
                
                issue_data = {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "description": issue.fields.description or "",
                    "status": {
                        "name": issue.fields.status.name if hasattr(issue.fields.status, 'name') else "Unknown"
                    },
                    "issuetype": {
                        "name": issue.fields.issuetype.name
                    },
                    "project": {
                        "key": issue.fields.project.key if hasattr(issue.fields.project, 'key') else "Unknown"
                    },
                    "created": getattr(issue.fields, 'created', None),
                    "updated": getattr(issue.fields, 'updated', None)
                }
                
                logger.debug(f"Extracted issue data structure: {issue_data}")
                
                # Verify the returned data is a dictionary
                if not isinstance(issue_data, dict):
                    logger.error(f"Unexpected issue_data type: {type(issue_data)}")
                    return None
                    
                return issue_data
                
            except AttributeError as e:
                logger.error(f"Failed to extract issue data - missing attribute: {str(e)}")
                logger.debug(f"Raw issue data: {vars(issue)}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get JIRA issue {issue_key}: {str(e)}")
            logger.exception("Full traceback:")
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