from pydantic import BaseModel, Field


class ResearchSummary(BaseModel):
    """Research summary for a user story"""
    pain_points: str = Field(..., description="Current pain points this story addresses")
    success_metrics: str = Field(..., description="Metrics to measure success")
    similar_implementations: str = Field(..., description="Similar implementations or references")
    modern_approaches: str = Field(..., description="Modern approaches and best practices to consider") 