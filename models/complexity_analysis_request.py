from pydantic import BaseModel

class ComplexityAnalysisRequest(BaseModel):
    """Request model for analyzing ticket complexity"""
    ticket_description: str 