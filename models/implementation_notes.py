from pydantic import BaseModel, Field


class ImplementationNotes(BaseModel):
    """Implementation notes for a user story"""
    technical_considerations: str = Field("", description="Key technical aspects to consider")
    integration_points: str = Field("", description="Integration requirements")
    accessibility: str = Field("", description="Accessibility requirements") 