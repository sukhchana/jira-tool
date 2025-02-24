from pydantic import BaseModel


class TicketGenerationResponse(BaseModel):
    """Response model containing the generated ticket structure"""
    summary: str
    description: str
    acceptance_criteria: str
    technical_notes: str
