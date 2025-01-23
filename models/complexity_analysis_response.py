from pydantic import BaseModel

class ComplexityAnalysisResponse(BaseModel):
    """Response model containing complexity analysis results"""
    analysis: str
    raw_response: str 