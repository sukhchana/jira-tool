from pydantic import BaseModel, Field


class StoryDescription(BaseModel):
    """Structured user story description"""
    role: str = Field(..., description="The user role/persona")
    goal: str = Field(..., description="What the user wants to accomplish")
    benefit: str = Field(..., description="The value/benefit to the user")
    formatted: str = Field(..., description="Formatted as: As a [role], I want [goal], so that [benefit]") 