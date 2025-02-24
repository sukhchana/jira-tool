from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import Field
from uuid_extensions import uuid7

from .base_model import BaseModel


class ProposedTicketMongo(BaseModel):
    """MongoDB model for a proposed ticket"""
    proposal_id: str = Field(default_factory=lambda: str(uuid7()), description="UUID7 of the proposal")
    ticket_id: str = Field(..., description="ID of the ticket (e.g. USER-STORY-1)")
    ticket_type: str = Field(..., description="Type of ticket: USER_STORY, TECHNICAL_TASK, or SUB_TASK")
    parent_id: Optional[str] = Field(None, description="ID of the parent ticket within the same proposal")

    # Common fields
    title: str
    description: str
    acceptance_criteria: List[str] = Field(default_factory=list)
    story_points: Optional[int] = None
    required_skills: List[str] = Field(default_factory=list)
    suggested_assignee: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    implementation_details: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # User Story specific fields
    scenarios: Optional[List[dict]] = None
    business_value: Optional[str] = None
    implementation_notes: Optional[str] = None
    complexity: Optional[str] = None
    technical_domain: Optional[str] = None
    modern_approaches: Optional[str] = None
    accessibility_requirements: Optional[str] = None
    integration_points: Optional[str] = None
    user_experience: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Technical Task specific fields
    modern_practices: Optional[str] = None
    security_considerations: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    epic_key: str = Field(..., description="The JIRA epic key this ticket belongs to")
    execution_id: str = Field(..., description="The execution ID this ticket was generated in")

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to ensure proper MongoDB serialization"""
        d = super().model_dump(*args, **kwargs)
        # Ensure created_at is a datetime object for MongoDB
        if isinstance(d['created_at'], str):
            d['created_at'] = datetime.fromisoformat(d['created_at'])
        return d

    class Config:
        json_schema_extra = {
            "example": {
                "proposal_id": "01HMW123ABC...",
                "ticket_id": "USER-STORY-1",
                "ticket_type": "USER_STORY",
                "parent_id": None,
                "title": "User Story - Login with Active Directory",
                "description": "As a user, I want to log in using my Active Directory credentials",
                "acceptance_criteria": ["- User can log in with AD credentials", "- Invalid credentials show error"],
                "story_points": 5,
                "required_skills": ["Python", "OAuth2", "Active Directory"],
                "suggested_assignee": "Backend Developer",
                "dependencies": ["Configure OAuth2 Client"],
                "scenarios": [
                    {
                        "name": "Successful Login",
                        "steps": [
                            {"keyword": "Given", "text": "user is on login page"},
                            {"keyword": "When", "text": "user enters valid AD credentials"},
                            {"keyword": "Then", "text": "user is logged in successfully"}
                        ]
                    }
                ],
                "business_value": "High",
                "complexity": "Medium",
                "technical_domain": "Authentication",
                "epic_key": "DP-7",
                "execution_id": "01HMW456XYZ..."
            }
        }
