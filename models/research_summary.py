from typing import Optional
from pydantic import BaseModel


class ResearchSummary(BaseModel):
    """Model for research summary structure"""
    pain_points: str
    success_metrics: str
    similar_implementations: str
    modern_approaches: str
    performance_considerations: Optional[str] = ""
    security_implications: Optional[str] = ""
    maintenance_aspects: Optional[str] = "" 